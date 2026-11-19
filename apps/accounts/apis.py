from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .exceptions import EmailAlreadyRegistered, InvalidVerificationToken


class RegisterInputSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class RegisterOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()


class VerifyEmailInputSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=1000)


class VerifyEmailOutputSerializer(serializers.Serializer):
    email_verified = serializers.BooleanField()


class RegisterApi(APIView):
    authentication_classes = []  # битый заголовок Authorization не должен ломать регистрацию
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterInputSerializer,
        responses={201: RegisterOutputSerializer},
        tags=["auth"],
    )
    def post(self, request):
        data = RegisterInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            user = services.user_register(**data.validated_data)
        except EmailAlreadyRegistered:
            raise ValidationError({"email": ["Пользователь с таким email уже существует."]})
        except DjangoValidationError as exc:
            raise ValidationError({"password": list(exc.messages)})
        out = RegisterOutputSerializer({"id": user.pk, "email": user.email})
        return Response(out.data, status=status.HTTP_201_CREATED)


class VerifyEmailApi(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyEmailInputSerializer,
        responses={200: VerifyEmailOutputSerializer},
        tags=["auth"],
    )
    def post(self, request):
        data = VerifyEmailInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.verify_email(token=data.validated_data["token"])
        except InvalidVerificationToken:
            raise ValidationError({"token": ["Токен недействителен или просрочен."]})
        return Response({"email_verified": True})
