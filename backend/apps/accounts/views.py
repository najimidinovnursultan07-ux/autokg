from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenObtainSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)
from .throttles import LoginAccountRateThrottle
from .two_factor import CODE_TTL, TwoFactorError, requires_two_factor, start_challenge, verify_challenge
from .tokens import (
    revoke_user_refresh_tokens,
    set_refresh_cookie,
)


# Публичной регистрации нет: аккаунты менеджеров создаёт администратор
# через /api/admin/managers/.


class LoginSerializer(TokenObtainPairSerializer):
    """Как обычный вход, но админу вместо токенов — второй шаг (код из Telegram)."""

    def validate(self, attrs):
        TokenObtainSerializer.validate(self, attrs)  # проверка пароля, ставит self.user
        if requires_two_factor(self.user):
            return {"two_factor_user": self.user}
        refresh = self.get_token(self.user)
        if jwt_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


def issue_tokens_response(user):
    refresh = RefreshToken.for_user(user)
    if jwt_settings.UPDATE_LAST_LOGIN:
        update_last_login(None, user)
    response = Response({"access": str(refresh.access_token)}, status=status.HTTP_200_OK)
    set_refresh_cookie(response, str(refresh))
    return response


class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, LoginAccountRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        data = serializer.validated_data

        user = data.get("two_factor_user")
        if user is not None:
            try:
                challenge = start_challenge(user, ip=request.META.get("REMOTE_ADDR", ""))
            except TwoFactorError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            return Response(
                {
                    "two_factor_required": True,
                    "challenge_id": str(challenge.id),
                    "expires_in": int(CODE_TTL.total_seconds()),
                },
                status=status.HTTP_200_OK,
            )

        response = Response({"access": data["access"]}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, data["refresh"])
        return response


class TwoFactorVerifyView(APIView):
    """Второй шаг входа админа: код из Telegram → токены."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_2fa"

    def post(self, request):
        try:
            user = verify_challenge(request.data.get("challenge_id"), request.data.get("code"))
        except TwoFactorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return issue_tokens_response(user)


class CookieTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        refresh = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not refresh:
            return Response(
                {"detail": "Refresh token is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data["refresh"] = refresh
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise AuthenticationFailed(
                "Refresh token is invalid or has already been used."
            ) from exc
        response_data = serializer.validated_data
        new_refresh = response_data.pop("refresh", None)
        response = Response(response_data, status=status.HTTP_200_OK)
        if new_refresh:
            set_refresh_cookie(response, new_refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if raw_refresh:
            try:
                refresh = RefreshToken(raw_refresh)
            except TokenError:
                refresh = None
            if refresh is not None:
                if str(refresh.get("user_id")) != str(request.user.pk):
                    return Response(
                        {"detail": "Refresh token does not belong to this user."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                refresh.blacklist()

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            key=settings.AUTH_COOKIE_NAME,
            path=settings.AUTH_COOKIE_PATH,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        return response


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class CsrfCookieView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = (
                f"{settings.PASSWORD_RESET_URL}?"
                f"{urlencode({'uid': uid, 'token': token})}"
            )
            send_mail(
                subject="Восстановление пароля AutoBuy",
                message=(
                    "Для установки нового пароля перейдите по ссылке. "
                    f"Если вы не запрашивали восстановление, проигнорируйте письмо:\n\n"
                    f"{reset_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return Response(
            {
                "detail": (
                    "Если аккаунт с таким адресом существует, "
                    "инструкция отправлена на электронную почту."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=("password", "updated_at"))
        revoke_user_refresh_tokens(user)
        response = Response(
            {"detail": "Пароль успешно изменён. Войдите с новым паролем."},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie(
            key=settings.AUTH_COOKIE_NAME,
            path=settings.AUTH_COOKIE_PATH,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        return response


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=("password", "updated_at"))
        revoke_user_refresh_tokens(user)

        response = Response(
            {"detail": "Пароль успешно изменён. Войдите снова."},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie(
            key=settings.AUTH_COOKIE_NAME,
            path=settings.AUTH_COOKIE_PATH,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        return response
