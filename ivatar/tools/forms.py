# -*- coding: utf-8 -*-
"""
Classes for our ivatar.tools.forms
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList

from ivatar.settings import AVATAR_MAX_SIZE
from ivatar.settings import MIN_LENGTH_URL, MAX_LENGTH_URL
from ivatar.settings import MIN_LENGTH_EMAIL, MAX_LENGTH_EMAIL


class CheckDomainForm(forms.Form):
    """
    Form handling domain check
    """

    domain = forms.CharField(
        label=_("Domain"),
        required=True,
        error_messages={"required": _("Cannot check without a domain name.")},
    )


class CheckForm(forms.Form):
    """
    Form handling check
    """

    mail = forms.EmailField(
        label=_("E-Mail"),
        required=False,
        min_length=MIN_LENGTH_EMAIL,
        max_length=MAX_LENGTH_EMAIL,
        error_messages={"required": _("Cannot check without a domain name.")},
    )

    openid = forms.CharField(
        label=_("OpenID"),
        required=False,
        min_length=MIN_LENGTH_URL,
        max_length=MAX_LENGTH_URL,
        error_messages={"required": _("Cannot check without an openid name.")},
    )

    size = forms.IntegerField(
        label=_("Size"),
        initial=80,
        min_value=5,
        max_value=AVATAR_MAX_SIZE,
        required=True,
    )

    default_opt = forms.ChoiceField(
        label=_("Default"),
        required=False,
        widget=forms.RadioSelect,
        choices=[
            ("retro", _("Retro style (similar to GitHub)")),
            ("robohash", _("Roboter style")),
            ("pagan", _("Retro adventure character")),
            ("wavatar", _("Wavatar style")),
            ("monsterid", _("Monster style")),
            ("identicon", _("Identicon style")),
            ("mm", _("Mystery man")),
            ("mmng", _("Mystery man NextGen")),
            ("none", _("None")),
        ],
    )

    default_url = forms.URLField(
        label=_("Default URL"),
        min_length=1,
        max_length=MAX_LENGTH_URL,
        required=False,
    )

    def clean(self):
        self.cleaned_data = super().clean()
        mail = self.cleaned_data.get("mail")
        openid = self.cleaned_data.get("openid")
        default_url = self.cleaned_data.get("default_url")
        default_opt = self.cleaned_data.get("default_opt")
        if default_url and default_opt and default_opt != "none":
            if "default_url" not in self._errors:
                self._errors["default_url"] = ErrorList()
            if "default_opt" not in self._errors:
                self._errors["default_opt"] = ErrorList()

            errstring = _("Only default URL OR default keyword may be specified")
            self._errors["default_url"].append(errstring)
            self._errors["default_opt"].append(errstring)
        if not mail and not openid:
            raise ValidationError(_("Either OpenID or mail must be specified"))
        return self.cleaned_data

    def clean_openid(self):
        data = self.cleaned_data["openid"]
        return data.lower()

    def clean_mail(self):
        data = self.cleaned_data["mail"]
        print(data)
        return data.lower()
