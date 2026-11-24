from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import apis, token_apis

urlpatterns = [
    path("auth/register/", apis.RegisterApi.as_view(), name="auth-register"),
    path("auth/verify-email/", apis.VerifyEmailApi.as_view(), name="auth-verify-email"),
    path("auth/token/", token_apis.LoginApi.as_view(), name="auth-token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/logout/", token_apis.LogoutApi.as_view(), name="auth-logout"),
]
