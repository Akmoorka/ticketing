from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .exceptions import SlugTaken


class OrganizationCreateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=50)


class OrganizationOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()


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
