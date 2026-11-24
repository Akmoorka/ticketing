from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from . import login_throttle


class InvalidCredentials(APIException):
    status_code = 401
    default_detail = "Неверный email или пароль."
    default_code = "invalid_credentials"


class LoginInputSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LogoutInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(max_length=2000)


class LoginApi(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginInputSerializer, responses={200: TokenPairSerializer}, tags=["auth"]
    )
    def post(self, request):
        data = LoginInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        email = data.validated_data["email"].strip().lower()
        ip = login_throttle.client_ip(request)
        login_throttle.check(ip, email)  # 429, если лимит уже исчерпан
        user = authenticate(request, email=email, password=data.validated_data["password"])
        if user is None:
            login_throttle.register_failure(ip, email)
            # один и тот же ответ для «нет такого email» и «неверный пароль»
            raise InvalidCredentials()
        login_throttle.reset(ip, email)
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class LogoutApi(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=LogoutInputSerializer, responses={204: None}, tags=["auth"])
    def post(self, request):
        data = LogoutInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            RefreshToken(data.validated_data["refresh"]).blacklist()
        except TokenError:
            raise ValidationError({"refresh": ["Токен недействителен или уже отозван."]})
        return Response(status=status.HTTP_204_NO_CONTENT)
