from contextlib import contextmanager

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import Conflict

from . import services
from .exceptions import (
    InvalidInvitation,
    InvitationNotForUser,
    LastOwner,
    MemberNotFound,
    OrganizationNotFound,
    RoleNotAllowed,
    SlugTaken,
)
from .models import Membership


class OrganizationCreateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=50)


class OrganizationOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()


class InvitationCreateInputSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class InvitationOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    role = serializers.CharField()
    expires_at = serializers.DateTimeField()


class InvitationAcceptOutputSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    role = serializers.CharField()


class OrganizationCreateApi(APIView):
    @extend_schema(
        request=OrganizationCreateInputSerializer,
        responses={201: OrganizationOutputSerializer},
        tags=["organizations"],
    )
    def post(self, request):
        data = OrganizationCreateInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            org = services.organization_create(user=request.user, **data.validated_data)
        except SlugTaken:
            raise ValidationError({"slug": ["Такой slug уже занят."]})
        out = OrganizationOutputSerializer(
            {"id": org.pk, "name": org.name, "slug": org.slug, "status": org.status}
        )
        return Response(out.data, status=status.HTTP_201_CREATED)


class InvitationCreateApi(APIView):
    @extend_schema(
        request=InvitationCreateInputSerializer,
        responses={201: InvitationOutputSerializer},
        tags=["organizations"],
    )
    def post(self, request, organization_id):
        data = InvitationCreateInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            inv = services.invitation_create(
                actor=request.user, organization_id=organization_id, **data.validated_data
            )
        except OrganizationNotFound:
            raise NotFound("Организация не найдена.")
        except RoleNotAllowed:
            raise PermissionDenied("Приглашать может только владелец организации.")
        out = InvitationOutputSerializer(
            {"id": inv.pk, "email": inv.email, "role": inv.role, "expires_at": inv.expires_at}
        )
        return Response(out.data, status=status.HTTP_201_CREATED)


class InvitationAcceptApi(APIView):
    @extend_schema(
        request=None,
        responses={200: InvitationAcceptOutputSerializer},
        tags=["organizations"],
    )
    def post(self, request, token):
        try:
            m = services.invitation_accept(user=request.user, token=token)
        except InvalidInvitation:
            raise ValidationError(
                {"token": ["Приглашение недействительно, просрочено или уже использовано."]}
            )
        except InvitationNotForUser:
            raise PermissionDenied(
                "Приглашение выписано на другой email, либо ваш email не подтверждён."
            )
        out = InvitationAcceptOutputSerializer(
            {"organization_id": m.organization_id, "role": m.role}
        )
        return Response(out.data)


class MemberRoleInputSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class MemberOutputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.CharField()


@contextmanager
def _translate_member_errors():
    try:
        yield
    except (OrganizationNotFound, MemberNotFound):
        raise NotFound("Не найдено.")
    except RoleNotAllowed:
        raise PermissionDenied("Управлять участниками может только владелец организации.")
    except LastOwner:
        raise Conflict("Нельзя удалить или понизить последнего владельца.", code="last_owner")


class MemberDetailApi(APIView):
    @extend_schema(
        request=MemberRoleInputSerializer,
        responses={200: MemberOutputSerializer},
        tags=["organizations"],
    )
    def patch(self, request, organization_id, user_id):
        data = MemberRoleInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with _translate_member_errors():
            m = services.member_change_role(
                actor=request.user,
                organization_id=organization_id,
                user_id=user_id,
                role=data.validated_data["role"],
            )
        return Response(MemberOutputSerializer({"user_id": m.user_id, "role": m.role}).data)

    @extend_schema(responses={204: None}, tags=["organizations"])
    def delete(self, request, organization_id, user_id):
        with _translate_member_errors():
            services.member_remove(
                actor=request.user, organization_id=organization_id, user_id=user_id
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
