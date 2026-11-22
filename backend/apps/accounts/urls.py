from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CsrfCookieView,
    CurrentUserView,
    EmailChangeView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TwoFactorVerifyView,
)


app_name = "accounts"

urlpatterns = [
    path("csrf/", CsrfCookieView.as_view(), name="csrf"),
    path("login/", csrf_exempt(CookieTokenObtainPairView.as_view()), name="login"),
    path("login/verify/", csrf_exempt(TwoFactorVerifyView.as_view()), name="login-verify"),
    path("refresh/", csrf_exempt(CookieTokenRefreshView.as_view()), name="refresh"),
    path("logout/", csrf_exempt(LogoutView.as_view()), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("profile/", CurrentUserView.as_view(), name="profile"),
    path("password-reset/", csrf_exempt(PasswordResetRequestView.as_view()), name="password-reset"),
    path(
        "password-reset/confirm/",
        csrf_exempt(PasswordResetConfirmView.as_view()),
        name="password-reset-confirm",
    ),
    path("email-change/", EmailChangeView.as_view(), name="email-change"),
    path("password-change/", csrf_exempt(PasswordChangeView.as_view()), name="password-change"),
]
