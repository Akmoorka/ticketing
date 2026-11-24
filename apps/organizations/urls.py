from django.urls import path

from . import apis

urlpatterns = [
    path("organizations/", apis.OrganizationCreateApi.as_view(), name="organization-create"),
]
