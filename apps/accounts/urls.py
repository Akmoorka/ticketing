from django.urls import path

from . import apis

urlpatterns = [
    path("auth/register/", apis.RegisterApi.as_view(), name="auth-register"),
    path("auth/verify-email/", apis.VerifyEmailApi.as_view(), name="auth-verify-email"),
]
