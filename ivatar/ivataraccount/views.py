# -*- coding: utf-8 -*-
"""
View classes for ivatar/ivataraccount/
"""
from io import BytesIO
from ivatar.utils import urlopen, Bluesky
import base64
import binascii
from xml.sax import saxutils
import gzip

from PIL import Image

from django.db.models import ProtectedError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.base import View, TemplateView
from django.views.generic.detail import DetailView
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import (
    PasswordResetView as PasswordResetViewOriginal,
)
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.shortcuts import render
from django_openid_auth.models import UserOpenID

from openid import oidutil
from openid.consumer import consumer

from ipware import get_client_ip

from email_validator import validate_email

from libravatar import libravatar_url
from ivatar.settings import (
    MAX_NUM_PHOTOS,
    MAX_PHOTO_SIZE,
    JPEG_QUALITY,
    AVATAR_MAX_SIZE,
)
from .gravatar import get_photo as get_gravatar_photo

from .forms import AddEmailForm, UploadPhotoForm, AddOpenIDForm
from .forms import UpdatePreferenceForm, UploadLibravatarExportForm
from .forms import DeleteAccountForm
from .models import UnconfirmedEmail, ConfirmedEmail, Photo
from .models import UnconfirmedOpenId, ConfirmedOpenId, DjangoOpenIDStore
from .models import UserPreference
from .models import file_format
from .read_libravatar_export import read_gzdata as libravatar_read_gzdata


def openid_logging(message, level=0):
    """
    Helper method for openid logging
    """
    # Normal messages are not that important
    # No need for coverage here
    if level > 0:  # pragma: no cover
        print(message)


class CreateView(SuccessMessageMixin, FormView):
    """
    View class for creating a new user
    """

    template_name = "new.html"
    form_class = UserCreationForm

    def form_valid(self, form):
        form.save()
        user = authenticate(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password1"],
        )
        if user is not None:
            # If the username looks like a mail address, automagically
            # add it as unconfirmed mail and set it also as user's
            # email address
            try:
                # This will error out if it's not a valid address
                valid = validate_email(form.cleaned_data["username"])
                user.email = valid.email
                user.save()
                # The following will also error out if it already exists
                unconfirmed = UnconfirmedEmail()
                unconfirmed.email = valid.email
                unconfirmed.user = user
                unconfirmed.save()
                unconfirmed.send_confirmation_mail(
                    url=self.request.build_absolute_uri("/")[:-1]
                )
            # In any exception cases, we just skip it
            except Exception:  # pylint: disable=broad-except
                pass

            login(self.request, user)
            pref = UserPreference.objects.create(
                user_id=user.pk
            )  # pylint: disable=no-member
            pref.save()
            return HttpResponseRedirect(reverse_lazy("profile"))
        return HttpResponseRedirect(reverse_lazy("login"))  # pragma: no cover

    def get(self, request, *args, **kwargs):
        """
        Handle get for create view
        """
        if request.user:
            if request.user.is_authenticated:
                return HttpResponseRedirect(reverse_lazy("profile"))
        return super().get(self, request, args, kwargs)


@method_decorator(login_required, name="dispatch")
class PasswordSetView(SuccessMessageMixin, FormView):
    """
    View class for changing the password
    """

    template_name = "password_change.html"
    form_class = SetPasswordForm
    success_message = _("password changed successfully - please login again")
    success_url = reverse_lazy("profile")

    def get_form_kwargs(self):
        kwargs = super(PasswordSetView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        super().form_valid(form)
        return HttpResponseRedirect(reverse_lazy("login"))


@method_decorator(login_required, name="dispatch")
class AddEmailView(SuccessMessageMixin, FormView):
    """
    View class for adding email addresses
    """

    template_name = "add_email.html"
    form_class = AddEmailForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        if not form.save(self.request):
            return render(self.request, self.template_name, {"form": form})

        messages.success(self.request, _("Address added successfully"))
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class RemoveUnconfirmedEmailView(SuccessMessageMixin, View):
    """
    View class for removing a unconfirmed email address
    """

    @staticmethod
    def post(request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post request - removing unconfirmed email
        """
        try:
            email = UnconfirmedEmail.objects.get(  # pylint: disable=no-member
                user=request.user, id=kwargs["email_id"]
            )
            email.delete()
            messages.success(request, _("Address removed"))
        except UnconfirmedEmail.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Address does not exist"))
        return HttpResponseRedirect(reverse_lazy("profile"))


class ConfirmEmailView(SuccessMessageMixin, TemplateView):
    """
    View class for confirming an unconfirmed email address
    """

    template_name = "email_confirmed.html"

    def get(self, request, *args, **kwargs):
        # be tolerant of extra crap added by mail clients
        key = kwargs["verification_key"].replace(" ", "")

        if len(key) != 64:
            messages.error(request, _("Verification key incorrect"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        try:
            unconfirmed = UnconfirmedEmail.objects.get(
                verification_key=key
            )  # pylint: disable=no-member
        except UnconfirmedEmail.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Verification key does not exist"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        if ConfirmedEmail.objects.filter(email=unconfirmed.email).count() > 0:
            messages.error(
                request,
                _("This mail address has been taken already and cannot be confirmed"),
            )
            return HttpResponseRedirect(reverse_lazy("profile"))

        # TODO: Check for a reasonable expiration time in unconfirmed email

        (confirmed_id, external_photos) = ConfirmedEmail.objects.create_confirmed_email(
            unconfirmed.user, unconfirmed.email, not request.user.is_anonymous
        )

        unconfirmed.delete()

        # if there's a single image in this user's profile,
        # assign it to the new email
        confirmed = ConfirmedEmail.objects.get(id=confirmed_id)
        if confirmed.user.photo_set.count() == 1:
            confirmed.set_photo(confirmed.user.photo_set.first())
        kwargs["photos"] = external_photos
        kwargs["email_id"] = confirmed_id
        return super().get(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class RemoveConfirmedEmailView(SuccessMessageMixin, View):
    """
    View class for removing a confirmed email address
    """

    @staticmethod
    def post(request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post request - removing confirmed email
        """
        try:
            email = ConfirmedEmail.objects.get(user=request.user, id=kwargs["email_id"])
            email.delete()
            messages.success(request, _("Address removed"))
        except ConfirmedEmail.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Address does not exist"))
        return HttpResponseRedirect(reverse_lazy("profile"))


@method_decorator(login_required, name="dispatch")
class AssignPhotoEmailView(SuccessMessageMixin, TemplateView):
    """
    View class for assigning a photo to an email address
    """

    model = Photo
    template_name = "assign_photo_email.html"

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post request - assign photo to email
        """
        photo = None

        try:
            email = ConfirmedEmail.objects.get(user=request.user, id=kwargs["email_id"])
        except ConfirmedEmail.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Invalid request"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        if "photoNone" in request.POST:
            email.photo = None
        else:
            if "photo_id" not in request.POST:
                messages.error(request, _("Invalid request [photo_id] missing"))
                return HttpResponseRedirect(reverse_lazy("profile"))

            try:
                photo = self.model.objects.get(  # pylint: disable=no-member
                    id=request.POST["photo_id"], user=request.user
                )
            except self.model.DoesNotExist:  # pylint: disable=no-member
                messages.error(request, _("Photo does not exist"))
                return HttpResponseRedirect(reverse_lazy("profile"))
            email.photo = photo
        email.bluesky_handle = None
        email.save()

        messages.success(request, _("Successfully changed photo"))
        return HttpResponseRedirect(reverse_lazy("profile"))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["email"] = ConfirmedEmail.objects.get(pk=kwargs["email_id"])
        return data


@method_decorator(login_required, name="dispatch")
class AssignPhotoOpenIDView(SuccessMessageMixin, TemplateView):
    """
    View class for assigning a photo to an openid address
    """

    model = Photo
    template_name = "assign_photo_openid.html"

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post - assign photo to openid
        """
        photo = None

        try:
            openid = ConfirmedOpenId.objects.get(  # pylint: disable=no-member
                user=request.user, id=kwargs["openid_id"]
            )
        except ConfirmedOpenId.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Invalid request"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        if "photoNone" in request.POST:
            openid.photo = None
        else:
            if "photo_id" not in request.POST:
                messages.error(request, _("Invalid request [photo_id] missing"))
                return HttpResponseRedirect(reverse_lazy("profile"))

            try:
                photo = self.model.objects.get(  # pylint: disable=no-member
                    id=request.POST["photo_id"], user=request.user
                )
            except self.model.DoesNotExist:  # pylint: disable=no-member
                messages.error(request, _("Photo does not exist"))
                return HttpResponseRedirect(reverse_lazy("profile"))
            openid.photo = photo
        openid.bluesky_handle = None
        openid.save()

        messages.success(request, _("Successfully changed photo"))
        return HttpResponseRedirect(reverse_lazy("profile"))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["openid"] = ConfirmedOpenId.objects.get(
            pk=kwargs["openid_id"]
        )  # pylint: disable=no-member
        return data


@method_decorator(login_required, name="dispatch")
class AssignBlueskyHandleToEmailView(SuccessMessageMixin, TemplateView):
    """
    View class for assigning a Bluesky handle to an email address
    """

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post request - assign bluesky handle to email
        """

        try:
            email = ConfirmedEmail.objects.get(user=request.user, id=kwargs["email_id"])
        except ConfirmedEmail.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Invalid request"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        if "bluesky_handle" not in request.POST:
            messages.error(request, _("Invalid request [bluesky_handle] missing"))
            return HttpResponseRedirect(reverse_lazy("profile"))
        bluesky_handle = request.POST["bluesky_handle"]

        try:
            bs = Bluesky()

            bs.get_avatar(bluesky_handle)
        except Exception as e:
            messages.error(
                request, _("Handle '%s' not found: %s" % (bluesky_handle, e))
            )
            return HttpResponseRedirect(reverse_lazy("profile"))
        email.set_bluesky_handle(bluesky_handle)
        email.photo = None
        email.save()

        messages.success(request, _("Successfully assigned Bluesky handle"))
        return HttpResponseRedirect(reverse_lazy("profile"))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["email"] = ConfirmedEmail.objects.get(pk=kwargs["email_id"])
        return data


@method_decorator(login_required, name="dispatch")
class AssignBlueskyHandleToOpenIdView(SuccessMessageMixin, TemplateView):
    """
    View class for assigning a Bluesky handle to an email address
    """

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post request - assign bluesky handle to email
        """

        try:
            openid = ConfirmedOpenId.objects.get(
                user=request.user, id=kwargs["open_id"]
            )
        except ConfirmedOpenId.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("Invalid request"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        if "bluesky_handle" not in request.POST:
            messages.error(request, _("Invalid request [bluesky_handle] missing"))
            return HttpResponseRedirect(reverse_lazy("profile"))
        bluesky_handle = request.POST["bluesky_handle"]

        try:
            bs = Bluesky()

            bs.get_avatar(bluesky_handle)
        except Exception as e:
            messages.error(
                request, _("Handle '%s' not found: %s" % (bluesky_handle, e))
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "assign_photo_openid", kwargs={"openid_id": int(kwargs["open_id"])}
                )
            )
        try:
            openid.set_bluesky_handle(bluesky_handle)
        except Exception as e:
            messages.error(request, _("Error: %s" % (e)))
            return HttpResponseRedirect(
                reverse_lazy(
                    "assign_photo_openid", kwargs={"openid_id": int(kwargs["open_id"])}
                )
            )
        openid.photo = None
        openid.save()

        messages.success(request, _("Successfully assigned Bluesky handle"))
        return HttpResponseRedirect(reverse_lazy("profile"))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["openid"] = ConfirmedOpenId.objects.get(pk=kwargs["open_id"])
        return data


@method_decorator(login_required, name="dispatch")
class ImportPhotoView(SuccessMessageMixin, TemplateView):
    """
    View class to import a photo from another service
    Currently only Gravatar is supported
    """

    template_name = "import_photo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["photos"] = []
        addr = None
        if "email_id" in kwargs:
            try:
                addr = ConfirmedEmail.objects.get(pk=kwargs["email_id"]).email
            except ConfirmedEmail.ObjectDoesNotExist:  # pylint: disable=no-member
                messages.error(self.request, _("Address does not exist"))
                return context

        addr = kwargs.get("email_addr", None)

        if addr:
            gravatar = get_gravatar_photo(addr)
            if gravatar:
                context["photos"].append(gravatar)

            libravatar_service_url = libravatar_url(
                email=addr,
                default=404,
                size=AVATAR_MAX_SIZE,
            )
            if libravatar_service_url:
                try:
                    urlopen(libravatar_service_url)
                except OSError as exc:
                    print("Exception caught during photo import: {}".format(exc))
                else:
                    context["photos"].append(
                        {
                            "service_url": libravatar_service_url,
                            "thumbnail_url": libravatar_service_url + "&s=80",
                            "image_url": libravatar_service_url + "&s=512",
                            "width": 80,
                            "height": 80,
                            "service_name": "Libravatar",
                        }
                    )

        return context

    def post(
        self, request, *args, **kwargs
    ):  # pylint: disable=no-self-use,unused-argument,too-many-branches,line-too-long
        """
        Handle post to photo import
        """

        imported = None

        email_id = kwargs.get("email_id", request.POST.get("email_id", None))
        addr = kwargs.get("emali_addr", request.POST.get("email_addr", None))

        if email_id:
            email = ConfirmedEmail.objects.filter(id=email_id, user=request.user)
            if email.exists():
                addr = email.first().email
            else:
                messages.error(request, _("Address does not exist"))
                return HttpResponseRedirect(reverse_lazy("profile"))

        if "photo_Gravatar" in request.POST:
            photo = Photo()
            photo.user = request.user
            photo.ip_address = get_client_ip(request)[0]
            if photo.import_image("Gravatar", addr):
                messages.success(request, _("Gravatar image successfully imported"))
            else:
                # Honestly, I'm not sure how to test this...
                messages.error(
                    request, _("Gravatar image import not successful")
                )  # pragma: no cover
            imported = True

        if "photo_Libravatar" in request.POST:
            photo = Photo()
            photo.user = request.user
            photo.ip_address = get_client_ip(request)[0]
            if photo.import_image("Libravatar", addr):
                messages.success(request, _("Libravatar image successfully imported"))
            else:
                # Honestly, I'm not sure how to test this...
                messages.error(
                    request, _("Libravatar image import not successful")
                )  # pragma: no cover
            imported = True
        if not imported:
            messages.warning(request, _("Nothing importable"))
        return HttpResponseRedirect(reverse_lazy("profile"))


@method_decorator(login_required, name="dispatch")
class RawImageView(DetailView):
    """
    View to return (binary) raw image data, for use in <img/>-tags
    """

    model = Photo

    def get(self, request, *args, **kwargs):
        photo = self.model.objects.get(pk=kwargs["pk"])  # pylint: disable=no-member
        if not photo.user.id == request.user.id and not request.user.is_staff:
            return HttpResponseRedirect(reverse_lazy("home"))
        return HttpResponse(BytesIO(photo.data), content_type="image/%s" % photo.format)


@method_decorator(login_required, name="dispatch")
class DeletePhotoView(SuccessMessageMixin, View):
    """
    View class for deleting a photo
    """

    model = Photo

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle get - delete photo
        """
        try:
            photo = self.model.objects.get(  # pylint: disable=no-member
                pk=kwargs["pk"], user=request.user
            )
            photo.delete()
        except (self.model.DoesNotExist, ProtectedError):  # pylint: disable=no-member
            messages.error(request, _("No such image or no permission to delete it"))
            return HttpResponseRedirect(reverse_lazy("profile"))
        messages.success(request, _("Photo deleted successfully"))
        return HttpResponseRedirect(reverse_lazy("profile"))


@method_decorator(login_required, name="dispatch")
class UploadPhotoView(SuccessMessageMixin, FormView):
    """
    View class responsible for photo upload
    """

    model = Photo
    template_name = "upload_photo.html"
    form_class = UploadPhotoForm
    success_message = _("Successfully uploaded")
    success_url = reverse_lazy("profile")

    def post(self, request, *args, **kwargs):
        num_photos = request.user.photo_set.count()
        if num_photos >= MAX_NUM_PHOTOS:
            messages.error(
                request, _("Maximum number of photos (%i) reached" % MAX_NUM_PHOTOS)
            )
            return HttpResponseRedirect(reverse_lazy("profile"))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        photo_data = self.request.FILES["photo"]
        if photo_data.size > MAX_PHOTO_SIZE:
            messages.error(self.request, _("Image too big"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        photo = form.save(self.request, photo_data)

        if not photo:
            messages.error(self.request, _("Invalid Format"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        # Override success URL -> Redirect to crop page.
        self.success_url = reverse_lazy("crop_photo", args=[photo.pk])
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class AddOpenIDView(SuccessMessageMixin, FormView):
    """
    View class for adding OpenID
    """

    template_name = "add_openid.html"
    form_class = AddOpenIDForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        openid_id = form.save(self.request.user)
        if not openid_id:
            return render(self.request, self.template_name, {"form": form})

        # At this point we have an unconfirmed OpenID, but
        # we do not add the message, that we successfully added it,
        # since this is misleading
        return HttpResponseRedirect(
            reverse_lazy("openid_redirection", args=[openid_id])
        )


@method_decorator(login_required, name="dispatch")
class RemoveUnconfirmedOpenIDView(View):
    """
    View class for removing a unconfirmed OpenID
    """

    model = UnconfirmedOpenId

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post - remove unconfirmed openid
        """
        try:
            openid = self.model.objects.get(  # pylint: disable=no-member
                user=request.user, id=kwargs["openid_id"]
            )
            openid.delete()
            messages.success(request, _("ID removed"))
        except self.model.DoesNotExist:  # pragma: no cover pylint: disable=no-member,line-too-long
            messages.error(request, _("ID does not exist"))
        return HttpResponseRedirect(reverse_lazy("profile"))


@method_decorator(login_required, name="dispatch")
class RemoveConfirmedOpenIDView(View):
    """
    View class for removing a confirmed OpenID
    """

    model = ConfirmedOpenId

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post - remove confirmed openid
        """
        try:
            openid = self.model.objects.get(  # pylint: disable=no-member
                user=request.user, id=kwargs["openid_id"]
            )
            try:
                openidobj = (
                    UserOpenID.objects.get(  # pylint: disable=no-member,line-too-long
                        user_id=request.user.id, claimed_id=openid.openid
                    )
                )
                openidobj.delete()
            except Exception as exc:  # pylint: disable=broad-except
                # Why it is not there?
                print("How did we get here: %s" % exc)
            openid.delete()
            messages.success(request, _("ID removed"))
        except self.model.DoesNotExist:  # pylint: disable=no-member
            messages.error(request, _("ID does not exist"))
        return HttpResponseRedirect(reverse_lazy("profile"))


@method_decorator(login_required, name="dispatch")
class RedirectOpenIDView(View):
    """
    Redirect view for OpenID
    """

    model = UnconfirmedOpenId

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle get for OpenID redirect view
        """
        try:
            unconfirmed = self.model.objects.get(  # pylint: disable=no-member
                user=request.user, id=kwargs["openid_id"]
            )
        except self.model.DoesNotExist:  # pragma: no cover  pylint: disable=no-member,line-too-long
            messages.error(request, _("ID does not exist"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        user_url = unconfirmed.openid
        session = {"id": request.session.session_key}

        oidutil.log = openid_logging
        openid_consumer = consumer.Consumer(session, DjangoOpenIDStore())

        try:
            auth_request = openid_consumer.begin(user_url)
        except consumer.DiscoveryFailure as exc:
            messages.error(request, _("OpenID discovery failed: %s" % exc))
            return HttpResponseRedirect(reverse_lazy("profile"))
        except UnicodeDecodeError as exc:  # pragma: no cover
            msg = _(
                "OpenID discovery failed (userid=%(userid)s) for "
                "%(userurl)s: %(message)s"
                % {
                    "userid": request.user.id,
                    "userurl": user_url.encode("utf-8"),
                    "message": exc,
                }
            )
            print("message: %s" % msg)
            messages.error(request, msg)

        if auth_request is None:  # pragma: no cover
            messages.error(request, _("OpenID discovery failed"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        realm = request.build_absolute_uri("/")[:-1]  # pragma: no cover
        return_url = realm + reverse(  # pragma: no cover
            "confirm_openid", args=[kwargs["openid_id"]]
        )
        return HttpResponseRedirect(  # pragma: no cover
            auth_request.redirectURL(realm, return_url)
        )


@method_decorator(login_required, name="dispatch")
class ConfirmOpenIDView(View):  # pragma: no cover
    """
    Confirm OpenID view
    """

    model = UnconfirmedOpenId
    model_confirmed = ConfirmedOpenId

    def do_request(self, data, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle request, called by get() or post()
        """
        session = {"id": self.request.session.session_key}
        current_url = self.request.build_absolute_uri("/")[:-1] + self.request.path
        openid_consumer = consumer.Consumer(session, DjangoOpenIDStore())
        info = openid_consumer.complete(data, current_url)
        if info.status == consumer.FAILURE:
            messages.error(
                self.request, _('Confirmation failed: "') + str(info.message) + '"'
            )
            return HttpResponseRedirect(reverse_lazy("profile"))

        if info.status == consumer.CANCEL:
            messages.error(self.request, _("Cancelled by user"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        if info.status != consumer.SUCCESS:
            messages.error(self.request, _("Unknown verification error"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        try:
            unconfirmed = self.model.objects.get(  # pylint: disable=no-member
                user=self.request.user, id=kwargs["openid_id"]
            )
        except self.model.DoesNotExist:  # pylint: disable=no-member
            messages.error(self.request, _("ID does not exist"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        # TODO: Check for a reasonable expiration time
        confirmed = self.model_confirmed()
        confirmed.user = unconfirmed.user
        confirmed.ip_address = get_client_ip(self.request)[0]
        confirmed.openid = unconfirmed.openid
        confirmed.save()

        unconfirmed.delete()

        # If there is a single image in this user's profile
        # assign it to the new id
        if self.request.user.photo_set.count() == 1:
            confirmed.set_photo(self.request.user.photo_set.first())

        # Also allow user to login using this OpenID (if not already taken)
        if not UserOpenID.objects.filter(  # pylint: disable=no-member
            claimed_id=confirmed.openid
        ).exists():
            user_openid = UserOpenID()
            user_openid.user = self.request.user
            user_openid.claimed_id = confirmed.openid
            user_openid.display_id = confirmed.openid
            user_openid.save()
        return HttpResponseRedirect(reverse_lazy("profile"))

    def get(self, request, *args, **kwargs):
        """
        Handle get - confirm openid
        """
        return self.do_request(request.GET, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle post - confirm openid
        """
        return self.do_request(request.POST, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class CropPhotoView(TemplateView):
    """
    View class for cropping photos
    """

    template_name = "crop_photo.html"
    success_url = reverse_lazy("profile")
    model = Photo

    def get(self, request, *args, **kwargs):
        photo = self.model.objects.get(
            pk=kwargs["pk"], user=request.user
        )  # pylint: disable=no-member
        email = request.GET.get("email")
        openid = request.GET.get("openid")
        return render(
            self.request,
            self.template_name,
            {
                "photo": photo,
                "email": email,
                "openid": openid,
            },
        )

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post - crop photo
        """
        photo = self.model.objects.get(
            pk=kwargs["pk"], user=request.user
        )  # pylint: disable=no-member
        dimensions = {
            "x": int(float(request.POST["x"])),
            "y": int(float(request.POST["y"])),
            "w": int(float(request.POST["w"])),
            "h": int(float(request.POST["h"])),
        }
        email = openid = None
        if "email" in request.POST:
            try:
                email = ConfirmedEmail.objects.get(email=request.POST["email"])
            except ConfirmedEmail.DoesNotExist:  # pylint: disable=no-member
                pass  # Ignore automatic assignment

        if "openid" in request.POST:
            try:
                openid = ConfirmedOpenId.objects.get(  # pylint: disable=no-member
                    openid=request.POST["openid"]
                )
            except ConfirmedOpenId.DoesNotExist:  # pylint: disable=no-member
                pass  # Ignore automatic assignment

        return photo.perform_crop(request, dimensions, email, openid)


@method_decorator(login_required, name="dispatch")  # pylint: disable=too-many-ancestors
class UserPreferenceView(FormView, UpdateView):
    """
    View class for user preferences view/update
    """

    template_name = "preferences.html"
    model = UserPreference
    form_class = UpdatePreferenceForm
    success_url = reverse_lazy("user_preference")

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Process POST-ed data from this form
        """
        userpref = None
        try:
            userpref = self.request.user.userpreference
        except ObjectDoesNotExist:
            userpref = UserPreference(user=self.request.user)
        userpref.theme = request.POST["theme"]
        userpref.save()
        try:
            if request.POST["email"] != self.request.user.email:
                addresses = list(
                    self.request.user.confirmedemail_set.all().values_list(
                        "email", flat=True
                    )
                )
                if request.POST["email"] not in addresses:
                    messages.error(
                        self.request,
                        _("Mail address not allowed: %s" % request.POST["email"]),
                    )
                else:
                    self.request.user.email = request.POST["email"]
                    self.request.user.save()
                    messages.info(self.request, _("Mail address changed."))
        except Exception as e:  # pylint: disable=broad-except
            messages.error(self.request, _("Error setting new mail address: %s" % e))

        try:
            if request.POST["first_name"] or request.POST["last_name"]:
                if request.POST["first_name"] != self.request.user.first_name:
                    self.request.user.first_name = request.POST["first_name"]
                    messages.info(self.request, _("First name changed."))
                if request.POST["last_name"] != self.request.user.last_name:
                    self.request.user.last_name = request.POST["last_name"]
                    messages.info(self.request, _("Last name changed."))
                self.request.user.save()
        except Exception as e:  # pylint: disable=broad-except
            messages.error(self.request, _("Error setting names: %s" % e))

        return HttpResponseRedirect(reverse_lazy("user_preference"))

    def get(self, request, *args, **kwargs):
        return render(
            self.request,
            self.template_name,
            {
                "THEMES": UserPreference.THEMES,
            },
        )

    def get_object(self, queryset=None):
        (obj, created) = UserPreference.objects.get_or_create(
            user=self.request.user
        )  # pylint: disable=no-member,unused-variable
        return obj


@method_decorator(login_required, name="dispatch")
class UploadLibravatarExportView(SuccessMessageMixin, FormView):
    """
    View class responsible for libravatar user data export upload
    """

    template_name = "upload_libravatar_export.html"
    form_class = UploadLibravatarExportForm
    success_message = _("Successfully uploaded")
    success_url = reverse_lazy("profile")
    model = User

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post request - choose items to import
        """
        if "save" in kwargs:  # pylint: disable=too-many-nested-blocks
            if kwargs["save"] == "save":
                for arg in request.POST:
                    if arg.startswith("email_"):
                        email = request.POST[arg]
                        if not ConfirmedEmail.objects.filter(
                            email=email
                        ) and not UnconfirmedEmail.objects.filter(
                            email=email
                        ):  # pylint: disable=no-member
                            try:
                                unconfirmed = UnconfirmedEmail.objects.create(  # pylint: disable=no-member
                                    user=request.user, email=email
                                )
                                unconfirmed.save()
                                unconfirmed.send_confirmation_mail(
                                    url=request.build_absolute_uri("/")[:-1]
                                )
                                messages.info(
                                    request,
                                    "%s: %s"
                                    % (
                                        email,
                                        _(
                                            "address added successfully,\
                                            confirmation mail sent"
                                        ),
                                    ),
                                )
                            except Exception as exc:  # pylint: disable=broad-except
                                # DEBUG
                                print(
                                    "Exception during adding mail address (%s): %s"
                                    % (email, exc)
                                )

                    if arg.startswith("photo"):
                        try:
                            data = base64.decodebytes(bytes(request.POST[arg], "utf-8"))
                        except binascii.Error as exc:
                            print("Cannot decode photo: %s" % exc)
                            continue
                        try:
                            pilobj = Image.open(BytesIO(data))
                            out = BytesIO()
                            pilobj.save(out, pilobj.format, quality=JPEG_QUALITY)
                            out.seek(0)
                            photo = Photo()
                            photo.user = request.user
                            photo.ip_address = get_client_ip(request)[0]
                            photo.format = file_format(pilobj.format)
                            photo.data = out.read()
                            photo.save()
                        except Exception as exc:  # pylint: disable=broad-except
                            print("Exception during save: %s" % exc)
                            continue

                return HttpResponseRedirect(reverse_lazy("profile"))
        return super().post(request, args, kwargs)

    def form_valid(self, form):
        data = self.request.FILES["export_file"]
        try:
            items = libravatar_read_gzdata(data.read())
            # DEBUG print(items)
            return render(
                self.request,
                "choose_libravatar_export.html",
                {
                    "emails": items["emails"],
                    "photos": items["photos"],
                },
            )
        except Exception as e:
            messages.error(self.request, _("Unable to parse file: %s" % e))
            return HttpResponseRedirect(reverse_lazy("upload_export"))


@method_decorator(login_required, name="dispatch")
class ResendConfirmationMailView(View):
    """
    View class for resending confirmation mail
    """

    model = UnconfirmedEmail

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle post - resend confirmation mail for unconfirmed e-mail address
        """
        try:
            email = self.model.objects.get(  # pylint: disable=no-member
                user=request.user, id=kwargs["email_id"]
            )
        except self.model.DoesNotExist:  # pragma: no cover  pylint: disable=no-member
            messages.error(request, _("ID does not exist"))
        else:
            try:
                email.send_confirmation_mail(url=request.build_absolute_uri("/")[:-1])
                messages.success(
                    request, "%s: %s" % (_("Confirmation mail sent to"), email.email)
                )
            except Exception as exc:  # pylint: disable=broad-except
                messages.error(
                    request,
                    "%s %s: %s"
                    % (_("Unable to send confirmation email for"), email.email, exc),
                )
        return HttpResponseRedirect(reverse_lazy("profile"))


class IvatarLoginView(LoginView):
    """
    View class for login
    """

    template_name = "login.html"

    def get(self, request, *args, **kwargs):
        """
        Handle get for login view
        """
        if request.user:
            if request.user.is_authenticated:
                return HttpResponseRedirect(reverse_lazy("profile"))
        return super().get(self, request, args, kwargs)


@method_decorator(login_required, name="dispatch")
class ProfileView(TemplateView):
    """
    View class for profile
    """

    template_name = "profile.html"

    def get(self, request, *args, **kwargs):
        if "profile_username" in kwargs:
            if not request.user.is_staff:
                return HttpResponseRedirect(reverse_lazy("profile"))
            try:
                u = User.objects.get(username=kwargs["profile_username"])
                request.user = u
            except Exception:  # pylint: disable=broad-except
                pass

        self._confirm_claimed_openid()
        return super().get(self, request, args, kwargs)

    def get_context_data(self, **kwargs):
        """
        Provide additional context data, like if max_photos is reached
        already or not.
        """
        context = super().get_context_data(**kwargs)
        context["max_photos"] = False
        if self.request.user:
            if self.request.user.photo_set.all().count() >= MAX_NUM_PHOTOS:
                context["max_photos"] = True
                return context

    def _confirm_claimed_openid(self):
        openids = self.request.user.useropenid_set.all()
        # If there is only one OpenID, we eventually need to add it to
        # the user account
        if openids.count() == 1:
            # Already confirmed, skip
            if ConfirmedOpenId.objects.filter(  # pylint: disable=no-member
                openid=openids.first().claimed_id
            ).exists():
                return
            # For whatever reason, this is in unconfirmed state, skip
            if UnconfirmedOpenId.objects.filter(  # pylint: disable=no-member
                openid=openids.first().claimed_id
            ).exists():
                return
            print("need to confirm: %s" % openids.first())
            confirmed = ConfirmedOpenId()
            confirmed.user = self.request.user
            confirmed.ip_address = get_client_ip(self.request)[0]
            confirmed.openid = openids.first().claimed_id
            confirmed.save()


class PasswordResetView(PasswordResetViewOriginal):
    """
    View class for password reset
    """

    def post(self, request, *args, **kwargs):
        """
        Since we have the mail addresses in ConfirmedEmail model,
        we need to set the email on the user object in order for the
        PasswordResetView class to pick up the correct user.
        In case we have the mail address in the User objecct, we still
        need to assign a random password in order for PasswordResetView
        class to pick up the user - else it will silently do nothing.
        """
        if "email" in request.POST:
            user = None

            # Try to find the user via the normal user class
            # TODO: How to handle the case that multiple user accounts
            # could have the same password set?
            user = User.objects.filter(email=request.POST["email"]).first()

            # If we didn't find the user in the previous step,
            # try the ConfirmedEmail class instead.
            # If we find the user there, we need to set the mail
            # attribute on the user object accordingly
            if not user:
                try:
                    confirmed_email = ConfirmedEmail.objects.get(
                        email=request.POST["email"]
                    )
                    user = confirmed_email.user
                    user.email = confirmed_email.email
                    user.save()
                except ObjectDoesNotExist:
                    pass

            # If we found the user, set a random password. Else, the
            # ResetPasswordView class will silently ignore the password
            # reset request
            if user:
                if not user.password or user.password.startswith("!"):
                    random_pass = User.objects.make_random_password()
                    user.set_password(random_pass)
                    user.save()

        # Whatever happens above, let the original function handle the rest
        return super().post(self, request, args, kwargs)


@method_decorator(login_required, name="dispatch")
class DeleteAccountView(SuccessMessageMixin, FormView):
    """
    View class for account deletion
    """

    template_name = "delete.html"
    form_class = DeleteAccountForm
    success_url = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        return super().get(self, request, args, kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle account deletion
        """
        if request.user.password:
            if "password" in request.POST:
                if not request.user.check_password(request.POST["password"]):
                    messages.error(request, _("Incorrect password"))
                    return HttpResponseRedirect(reverse_lazy("delete"))
            else:
                messages.error(request, _("No password given"))
                return HttpResponseRedirect(reverse_lazy("delete"))

                raise _("No password given")
        # should delete all confirmed/unconfirmed/photo objects
        request.user.delete()
        return super().post(self, request, args, kwargs)


@method_decorator(login_required, name="dispatch")
class ExportView(SuccessMessageMixin, TemplateView):
    """
    View class responsible for libravatar user data export
    """

    template_name = "export.html"
    model = User

    def get(self, request, *args, **kwargs):
        return super().get(self, request, args, kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle real export
        """
        SCHEMA_ROOT = "https://www.libravatar.org/schemas/export/0.2"
        SCHEMA_XSD = "%s/export.xsd" % SCHEMA_ROOT

        def xml_header():
            return (
                """<?xml version="1.0" encoding="UTF-8"?>"""
                '''<user xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'''
                ''' xsi:schemaLocation="%s %s"'''
                """ xmlns="%s">\n""" % (SCHEMA_ROOT, SCHEMA_XSD, SCHEMA_ROOT)
            )

        def xml_footer():
            return "</user>\n"

        def xml_account(user):
            escaped_username = saxutils.quoteattr(user.username)
            escaped_password = saxutils.quoteattr(user.password)
            return "  <account username=%s password=%s/>\n" % (
                escaped_username,
                escaped_password,
            )

        def xml_email(user):
            returnstring = "  <emails>\n"
            for email in user.confirmedemail_set.all():
                returnstring += (
                    '    <email photo_id="'
                    + str(email.photo_id)
                    + '">'
                    + str(email.email)
                    + "</email>"
                    + "\n"
                )
            returnstring += "  </emails>\n"
            return returnstring

        def xml_openid(user):
            returnstring = "  <openids>\n"
            for openid in user.confirmedopenid_set.all():
                returnstring += (
                    '    <openid photo_id="'
                    + str(openid.photo_id)
                    + '">'
                    + str(openid.openid)
                    + "</openid>"
                    + "\n"
                )
            returnstring += "  </openids>\n"
            return returnstring

        def xml_photos(user):
            s = "  <photos>\n"
            for photo in user.photo_set.all():
                encoded_photo = base64.b64encode(photo.data)
                if encoded_photo:
                    s += (
                        """    <photo id="%s" encoding="base64" format=%s>"""
                        """%s"""
                        """</photo>\n"""
                        % (photo.id, saxutils.quoteattr(photo.format), encoded_photo)
                    )
            s += "  </photos>\n"
            return s

        user = request.user

        photos = []
        for photo in user.photo_set.all():
            photo_details = {"data": photo.data, "format": photo.format}
            photos.append(photo_details)

        bytesobj = BytesIO()
        data = gzip.GzipFile(fileobj=bytesobj, mode="w")
        data.write(bytes(xml_header(), "utf-8"))
        data.write(bytes(xml_account(user), "utf-8"))
        data.write(bytes(xml_email(user), "utf-8"))
        data.write(bytes(xml_openid(user), "utf-8"))
        data.write(bytes(xml_photos(user), "utf-8"))
        data.write(bytes(xml_footer(), "utf-8"))
        data.close()
        bytesobj.seek(0)

        response = HttpResponse(content_type="application/gzip")
        response["Content-Disposition"] = (
            'attachment; filename="libravatar-export_%s.xml.gz"' % user.username
        )
        response.write(bytesobj.read())
        return response
