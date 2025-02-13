# -*- coding: utf-8 -*-
"""
Classes for our ivatar.ivataraccount.forms
"""
from urllib.parse import urlsplit, urlunsplit

from django import forms
from django.utils.translation import gettext_lazy as _

from ipware import get_client_ip

from ivatar import settings
from ivatar.settings import MIN_LENGTH_EMAIL, MAX_LENGTH_EMAIL
from ivatar.settings import MIN_LENGTH_URL, MAX_LENGTH_URL
from .models import UnconfirmedEmail, ConfirmedEmail, Photo
from .models import UnconfirmedOpenId, ConfirmedOpenId
from .models import UserPreference


MAX_NUM_UNCONFIRMED_EMAILS_DEFAULT = 5


class AddEmailForm(forms.Form):
    """
    Form to handle adding email addresses
    """

    email = forms.EmailField(
        label=_("Email"),
        min_length=MIN_LENGTH_EMAIL,
        max_length=MAX_LENGTH_EMAIL,
    )

    def clean_email(self):
        """
        Enforce lowercase email
        """
        # TODO: Domain restriction as in libravatar?
        return self.cleaned_data["email"].lower()

    def save(self, request):
        """
        Save the model, ensuring some safety
        """
        user = request.user
        # Enforce the maximum number of unconfirmed emails a user can have
        num_unconfirmed = user.unconfirmedemail_set.count()

        max_num_unconfirmed_emails = getattr(
            settings, "MAX_NUM_UNCONFIRMED_EMAILS", MAX_NUM_UNCONFIRMED_EMAILS_DEFAULT
        )

        if num_unconfirmed >= max_num_unconfirmed_emails:
            self.add_error(None, _("Too many unconfirmed mail addresses!"))
            return False

        # Check whether or not a confirmation email has been
        # sent by this user already
        if UnconfirmedEmail.objects.filter(  # pylint: disable=no-member
            user=user, email=self.cleaned_data["email"]
        ).exists():
            self.add_error("email", _("Address already added, currently unconfirmed"))
            return False

        # Check whether or not the email is already confirmed (by someone)
        check_mail = ConfirmedEmail.objects.filter(email=self.cleaned_data["email"])
        if check_mail.exists():
            msg = _("Address already confirmed (by someone else)")
            if check_mail.first().user == request.user:
                msg = _("Address already confirmed (by you)")
            self.add_error("email", msg)
            return False

        unconfirmed = UnconfirmedEmail()
        unconfirmed.email = self.cleaned_data["email"]
        unconfirmed.user = user
        unconfirmed.save()
        unconfirmed.send_confirmation_mail(url=request.build_absolute_uri("/")[:-1])
        return True


class UploadPhotoForm(forms.Form):
    """
    Form handling photo upload
    """

    photo = forms.FileField(
        label=_("Photo"),
        error_messages={"required": _("You must choose an image to upload.")},
    )
    not_porn = forms.BooleanField(
        label=_("suitable for all ages (i.e. no offensive content)"),
        required=True,
        error_messages={
            "required": _(
                'We only host "G-rated" images and so this field must be checked.'
            )
        },
    )
    can_distribute = forms.BooleanField(
        label=_("can be freely copied"),
        required=True,
        error_messages={
            "required": _(
                "This field must be checked since we need to be able to distribute photos to third parties."
            )
        },
    )

    @staticmethod
    def save(request, data):
        """
        Save the model and assign it to the current user
        """
        # Link this file to the user's profile
        photo = Photo()
        photo.user = request.user
        photo.ip_address = get_client_ip(request)[0]
        photo.data = data.read()
        photo.save()
        return photo if photo.pk else None


class AddOpenIDForm(forms.Form):
    """
    Form to handle adding OpenID
    """

    openid = forms.URLField(
        label=_("OpenID"),
        min_length=MIN_LENGTH_URL,
        max_length=MAX_LENGTH_URL,
        initial="http://",
    )

    def clean_openid(self):
        """
        Enforce restrictions
        """
        # Lowercase hostname port of the URL
        url = urlsplit(self.cleaned_data["openid"])
        return urlunsplit(
            (
                url.scheme.lower(),
                url.netloc.lower(),
                url.path,
                url.query,
                url.fragment,
            )
        )

    def save(self, user):
        """
        Save the model, ensuring some safety
        """
        if ConfirmedOpenId.objects.filter(  # pylint: disable=no-member
            openid=self.cleaned_data["openid"]
        ).exists():
            self.add_error("openid", _("OpenID already added and confirmed!"))
            return False

        if UnconfirmedOpenId.objects.filter(  # pylint: disable=no-member
            openid=self.cleaned_data["openid"]
        ).exists():
            self.add_error("openid", _("OpenID already added, but not confirmed yet!"))
            return False

        unconfirmed = UnconfirmedOpenId()
        unconfirmed.openid = self.cleaned_data["openid"]
        unconfirmed.user = user
        unconfirmed.save()

        return unconfirmed.pk


class UpdatePreferenceForm(forms.ModelForm):
    """
    Form for updating user preferences
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Meta class for UpdatePreferenceForm
        """

        model = UserPreference
        fields = ["theme"]


class UploadLibravatarExportForm(forms.Form):
    """
    Form handling libravatar user export upload
    """

    export_file = forms.FileField(
        label=_("Export file"),
        error_messages={"required": _("You must choose an export file to upload.")},
    )
    not_porn = forms.BooleanField(
        label=_("suitable for all ages (i.e. no offensive content)"),
        required=True,
        error_messages={
            "required": _(
                'We only host "G-rated" images and so this field must be checked.'
            )
        },
    )
    can_distribute = forms.BooleanField(
        label=_("can be freely copied"),
        required=True,
        error_messages={
            "required": _(
                "This field must be checked since we need to be able to\
              distribute photos to third parties."
            )
        },
    )


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Password"), required=False, widget=forms.PasswordInput()
    )
