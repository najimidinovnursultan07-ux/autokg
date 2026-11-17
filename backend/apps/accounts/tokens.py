from django.conf import settings
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken


def set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=str(refresh_token),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_COOKIE_PATH,
    )


def issue_token_pair(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def revoke_user_refresh_tokens(user):
    outstanding_tokens = OutstandingToken.objects.filter(user=user)
    BlacklistedToken.objects.bulk_create(
        [
            BlacklistedToken(token=outstanding_token)
            for outstanding_token in outstanding_tokens
        ],
        ignore_conflicts=True,
    )
