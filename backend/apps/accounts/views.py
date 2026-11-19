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
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)
from .tokens import (
    revoke_user_refresh_tokens,
    set_refresh_cookie,
)


# Публичной регистрации нет: аккаунты менеджеров создаёт администратор
# через /api/admin/managers/.


class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh = response.data.pop("refresh")
            set_refresh_cookie(response, refresh)
        return response


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
                subject="Восстановление пароля AutoKG",
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
