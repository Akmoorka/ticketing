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
        "organizations/<int:organization_id>/members/<int:user_id>/",
        apis.MemberDetailApi.as_view(),
        name="member-detail",
    ),
    path(
        "invitations/<str:token>/accept/",
        apis.InvitationAcceptApi.as_view(),
        name="invitation-accept",
    ),
]
