# -*- coding: utf-8 -*-
"""
URLs for ivatar.ivataraccount
"""
from django.urls import path, re_path

from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import (
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView

from .views import ProfileView, PasswordResetView
from .views import CreateView, PasswordSetView, AddEmailView
from .views import RemoveUnconfirmedEmailView, ConfirmEmailView
from .views import RemoveConfirmedEmailView, AssignPhotoEmailView
from .views import RemoveUnconfirmedOpenIDView, RemoveConfirmedOpenIDView
from .views import ImportPhotoView, RawImageView, DeletePhotoView
from .views import UploadPhotoView, AssignPhotoOpenIDView
from .views import AddOpenIDView, RedirectOpenIDView, ConfirmOpenIDView
from .views import CropPhotoView
from .views import UserPreferenceView, UploadLibravatarExportView
from .views import ResendConfirmationMailView
from .views import IvatarLoginView
from .views import DeleteAccountView
from .views import ExportView
from .avatar_creator_views import AvatarCreatorView, AvatarView

# from .avatar_creator_views import AvatarItemView

# Define URL patterns, self documenting
# To see the fancy, colorful evaluation of these use:
# ./manager show_urls
urlpatterns = [  # pylint: disable=invalid-name
    path("new/", CreateView.as_view(), name="new_account"),
    path("login/", IvatarLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path(
        "password_change/",
        PasswordChangeView.as_view(template_name="password_change.html"),
        name="password_change",
    ),
    path(
        "password_change/done/",
        PasswordChangeDoneView.as_view(template_name="password_change_done.html"),
        name="password_change_done",
    ),
    path(
        "password_reset/",
        PasswordResetView.as_view(template_name="password_reset.html"),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        PasswordResetDoneView.as_view(template_name="password_reset_submitted.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(template_name="password_change.html"),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        PasswordResetCompleteView.as_view(template_name="password_change_done.html"),
        name="password_reset_complete",
    ),
    path(
        "export/",
        ExportView.as_view(),
        name="export",
    ),
    path("delete/", DeleteAccountView.as_view(), name="delete"),
    path("profile/", ProfileView.as_view(), name="profile"),
    re_path(
        "profile/(?P<profile_username>.+)",
        ProfileView.as_view(),
        name="profile_with_profile_username",
    ),
    path("add_email/", AddEmailView.as_view(), name="add_email"),
    path("add_openid/", AddOpenIDView.as_view(), name="add_openid"),
    path("upload_photo/", UploadPhotoView.as_view(), name="upload_photo"),
    path("password_set/", PasswordSetView.as_view(), name="password_set"),
    path("avatar_creator/", AvatarCreatorView.as_view(), name="avatar_creator"),
    path("avatar_view/", AvatarView.as_view(), name="avataaar"),
    # This is for testing purpose only and shall not be used in production at all
    # path("avatar_item_view/", AvatarItemView.as_view(), name="avataaar_item"),
    re_path(
        r"remove_unconfirmed_openid/(?P<openid_id>\d+)",
        RemoveUnconfirmedOpenIDView.as_view(),
        name="remove_unconfirmed_openid",
    ),
    re_path(
        r"remove_confirmed_openid/(?P<openid_id>\d+)",
        RemoveConfirmedOpenIDView.as_view(),
        name="remove_confirmed_openid",
    ),
    re_path(
        r"openid_redirection/(?P<openid_id>\d+)",
        RedirectOpenIDView.as_view(),
        name="openid_redirection",
    ),
    re_path(
        r"confirm_openid/(?P<openid_id>\w+)",
        ConfirmOpenIDView.as_view(),
        name="confirm_openid",
    ),
    re_path(
        r"confirm_email/(?P<verification_key>\w+)",
        ConfirmEmailView.as_view(),
        name="confirm_email",
    ),
    re_path(
        r"remove_unconfirmed_email/(?P<email_id>\d+)",
        RemoveUnconfirmedEmailView.as_view(),
        name="remove_unconfirmed_email",
    ),
    re_path(
        r"remove_confirmed_email/(?P<email_id>\d+)",
        RemoveConfirmedEmailView.as_view(),
        name="remove_confirmed_email",
    ),
    re_path(
        r"assign_photo_email/(?P<email_id>\d+)",
        AssignPhotoEmailView.as_view(),
        name="assign_photo_email",
    ),
    re_path(
        r"assign_photo_openid/(?P<openid_id>\d+)",
        AssignPhotoOpenIDView.as_view(),
        name="assign_photo_openid",
    ),
    re_path(r"import_photo/$", ImportPhotoView.as_view(), name="import_photo"),
    re_path(
        r"import_photo/(?P<email_addr>[\w.+-]+@[\w.]+.[\w.]+)",
        ImportPhotoView.as_view(),
        name="import_photo",
    ),
    re_path(
        r"import_photo/(?P<email_id>\d+)",
        ImportPhotoView.as_view(),
        name="import_photo",
    ),
    re_path(
        r"delete_photo/(?P<pk>\d+)", DeletePhotoView.as_view(), name="delete_photo"
    ),
    re_path(r"raw_image/(?P<pk>\d+)", RawImageView.as_view(), name="raw_image"),
    re_path(r"crop_photo/(?P<pk>\d+)", CropPhotoView.as_view(), name="crop_photo"),
    re_path(r"pref/$", UserPreferenceView.as_view(), name="user_preference"),
    re_path(
        r"upload_export/$", UploadLibravatarExportView.as_view(), name="upload_export"
    ),
    re_path(
        r"upload_export/(?P<save>save)$",
        UploadLibravatarExportView.as_view(),
        name="upload_export",
    ),
    re_path(
        r"resend_confirmation_mail/(?P<email_id>\d+)",
        ResendConfirmationMailView.as_view(),
        name="resend_confirmation_mail",
    ),
]
