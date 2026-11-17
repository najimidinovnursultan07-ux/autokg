from django.urls import path

from .views import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CsrfCookieView,
    CurrentUserView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegistrationView,
)


app_name = "accounts"

urlpatterns = [
    path("csrf/", CsrfCookieView.as_view(), name="csrf"),
    path("register/", RegistrationView.as_view(), name="register"),
    path("login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("profile/", CurrentUserView.as_view(), name="profile"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password-change/", PasswordChangeView.as_view(), name="password-change"),
]
