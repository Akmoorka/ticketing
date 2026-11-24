from django.urls import path

from . import apis

urlpatterns = [
    path("organizations/", apis.OrganizationCreateApi.as_view(), name="organization-create"),
    path(
        "organizations/<int:organization_id>/invitations/",
        apis.InvitationCreateApi.as_view(),
        name="invitation-create",
    ),
    path(
        "invitations/<str:token>/accept/",
        apis.InvitationAcceptApi.as_view(),
        name="invitation-accept",
    ),
]
