# -*- coding: utf-8 -*-
"""
Our models for ivatar.ivataraccount
"""

import base64
import hashlib
import time
from io import BytesIO
from os import urandom
from urllib.error import HTTPError, URLError
from ivatar.utils import urlopen, Bluesky
from urllib.parse import urlsplit, urlunsplit

from PIL import Image
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.template.loader import render_to_string
from openid.association import Association as OIDAssociation
from openid.store import nonce as oidnonce
from openid.store.interface import OpenIDStore

from libravatar import libravatar_url

from ivatar.settings import MAX_LENGTH_EMAIL, logger
from ivatar.settings import MAX_PIXELS, AVATAR_MAX_SIZE, JPEG_QUALITY
from ivatar.settings import MAX_LENGTH_URL
from ivatar.settings import SECURE_BASE_URL, SITE_NAME, DEFAULT_FROM_EMAIL
from ivatar.utils import openid_variations
from .gravatar import get_photo as get_gravatar_photo


def file_format(image_type):
    """
    Helper method returning a short image type
    """
    if image_type in ("JPEG", "MPO"):
        return "jpg"
    elif image_type == "PNG":
        return "png"
    elif image_type == "GIF":
        return "gif"
    elif image_type == "WEBP":
        return "webp"
    return None


def pil_format(image_type):
    """
    Helper method returning the 'encoder name' for PIL
    """
    if image_type in ("jpg", "jpeg", "mpo"):
        return "JPEG"
    elif image_type == "png":
        return "PNG"
    elif image_type == "gif":
        return "GIF"
    elif image_type == "webp":
        return "WEBP"

    logger.info("Unsupported file format: %s", image_type)
    return None


class UserPreference(models.Model):
    """
    Holds the user users preferences
    """

    THEMES = (
        ("default", "Default theme"),
        ("clime", "climes theme"),
        ("green", "green theme"),
        ("red", "red theme"),
    )

    theme = models.CharField(
        max_length=10,
        choices=THEMES,
        default="default",
    )

    user = models.OneToOneField(
        User,
        on_delete=models.deletion.CASCADE,
        primary_key=True,
    )

    def __str__(self):
        return "Preference (%i) for %s" % (self.pk, self.user)


class BaseAccountModel(models.Model):
    """
    Base, abstract model, holding fields we use in all cases
    """

    user = models.ForeignKey(
        User,
        on_delete=models.deletion.CASCADE,
    )
    ip_address = models.GenericIPAddressField(unpack_ipv4=True, null=True)
    add_date = models.DateTimeField(default=timezone.now)

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Class attributes
        """

        abstract = True


class Photo(BaseAccountModel):
    """
    Model holding the photos and information about them
    """

    ip_address = models.GenericIPAddressField(unpack_ipv4=True)
    data = models.BinaryField()
    format = models.CharField(max_length=4)
    access_count = models.BigIntegerField(default=0, editable=False)

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Class attributes
        """

        verbose_name = _("photo")
        verbose_name_plural = _("photos")

    def import_image(self, service_name, email_address):
        """
        Allow to import image from other (eg. Gravatar) service
        """
        image_url = False

        if service_name == "Gravatar":
            if gravatar := get_gravatar_photo(email_address):
                image_url = gravatar["image_url"]

        if service_name == "Libravatar":
            image_url = libravatar_url(email_address, size=AVATAR_MAX_SIZE)

        if not image_url:
            return False  # pragma: no cover
        try:
            image = urlopen(image_url)
        except HTTPError as exc:
            print(f"{service_name} import failed with an HTTP error: {exc.code}")
            return False
        except URLError as exc:
            print(f"{service_name} import failed: {exc.reason}")
            return False
        data = image.read()

        try:
            img = Image.open(BytesIO(data))
        # How am I supposed to test this?
        except ValueError:  # pragma: no cover
            return False  # pragma: no cover

        self.format = file_format(img.format)
        if not self.format:
            print(f"Unable to determine format: {img}")
            return False  # pragma: no cover
        self.data = data
        super().save()
        return True

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        """
        Override save from parent, taking care about the image
        """
        # Use PIL to read the file format
        try:
            img = Image.open(BytesIO(self.data))
        except Exception as exc:  # pylint: disable=broad-except
            # For debugging only
            print(f"Exception caught in Photo.save(): {exc}")
            return False
        self.format = file_format(img.format)
        if not self.format:
            print("Format not recognized")
            return False
        return super().save(force_insert, force_update, using, update_fields)

    def perform_crop(self, request, dimensions, email, openid):
        """
        Helper to crop the image
        """
        if request.user.photo_set.count() == 1:
            # This is the first photo, assign to all confirmed addresses
            for addr in request.user.confirmedemail_set.all():
                addr.photo = self
                addr.save()

            for addr in request.user.confirmedopenid_set.all():
                addr.photo = self
                addr.save()

        if email:
            # Explicitly asked
            email.photo = self
            email.save()

        if openid:
            # Explicitly asked
            openid.photo = self
            openid.save()

        # Do the real work cropping
        img = Image.open(BytesIO(self.data))

        # This should be anyway checked during save...
        dimensions["a"], dimensions["b"] = img.size  # pylint: disable=invalid-name
        if dimensions["a"] > MAX_PIXELS or dimensions["b"] > MAX_PIXELS:
            messages.error(
                request,
                _(
                    "Image dimensions are too big (max: %(max_pixels)s x %(max_pixels)s"
                    % {
                        "max_pixels": MAX_PIXELS,
                    }
                ),
            )
            return HttpResponseRedirect(reverse_lazy("profile"))

        if dimensions["w"] == 0 and dimensions["h"] == 0:
            dimensions["w"], dimensions["h"] = dimensions["a"], dimensions["b"]
            min_from_w_h = min(dimensions["w"], dimensions["h"])
            dimensions["w"], dimensions["h"] = min_from_w_h, min_from_w_h
        elif (
            (dimensions["w"] < 0)
            or ((dimensions["x"] + dimensions["w"]) > dimensions["a"])
            or (dimensions["h"] < 0)
            or ((dimensions["y"] + dimensions["h"]) > dimensions["b"])
        ):
            messages.error(request, _("Crop outside of original image bounding box"))
            return HttpResponseRedirect(reverse_lazy("profile"))

        cropped = img.crop(
            (
                dimensions["x"],
                dimensions["y"],
                dimensions["x"] + dimensions["w"],
                dimensions["y"] + dimensions["h"],
            )
        )
        # cropped.load()
        # Resize the image only if it's larger than the specified max width.
        cropped_w, cropped_h = cropped.size
        max_w = AVATAR_MAX_SIZE
        if cropped_w > max_w or cropped_h > max_w:
            cropped = cropped.resize((max_w, max_w), Image.LANCZOS)

        data = BytesIO()
        cropped.save(data, pil_format(self.format), quality=JPEG_QUALITY)
        data.seek(0)

        # Overwrite the existing image
        self.data = data.read()
        self.save()

        return HttpResponseRedirect(reverse_lazy("profile"))

    def __str__(self):
        return "%s (%i) from %s" % (self.format, self.pk or 0, self.user)


# pylint: disable=too-few-public-methods
class ConfirmedEmailManager(models.Manager):
    """
    Manager for our confirmed email addresses model
    """

    @staticmethod
    def create_confirmed_email(user, email_address, is_logged_in):
        """
        Helper method to create confirmed email address
        """
        confirmed = ConfirmedEmail()
        confirmed.user = user
        confirmed.ip_address = "0.0.0.0"
        confirmed.email = email_address
        confirmed.save()

        external_photos = []
        if is_logged_in:
            if gravatar := get_gravatar_photo(confirmed.email):
                external_photos.append(gravatar)

        return (confirmed.pk, external_photos)


class ConfirmedEmail(BaseAccountModel):
    """
    Model holding our confirmed email addresses, as well as the relation
    to the assigned photo
    """

    email = models.EmailField(unique=True, max_length=MAX_LENGTH_EMAIL)
    photo = models.ForeignKey(
        Photo,
        related_name="emails",
        blank=True,
        null=True,
        on_delete=models.deletion.SET_NULL,
    )
    # Alternative assignment - use Bluesky handle
    bluesky_handle = models.CharField(max_length=256, null=True, blank=True)
    digest = models.CharField(max_length=32)
    digest_sha256 = models.CharField(max_length=64)
    objects = ConfirmedEmailManager()
    access_count = models.BigIntegerField(default=0, editable=False)

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Class attributes
        """

        verbose_name = _("confirmed email")
        verbose_name_plural = _("confirmed emails")

    def set_photo(self, photo):
        """
        Helper method to set photo
        """
        self.photo = photo
        self.save()

    def set_bluesky_handle(self, handle):
        """
        Helper method to set Bluesky handle
        """

        bs = Bluesky()
        handle = bs.normalize_handle(handle)
        avatar = bs.get_profile(handle)
        if not avatar:
            raise Exception("Invalid Bluesky handle")
        self.bluesky_handle = handle
        self.save()

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        """
        Override save from parent, add digest
        """
        self.digest = hashlib.md5(
            self.email.strip().lower().encode("utf-8")
        ).hexdigest()
        self.digest_sha256 = hashlib.sha256(
            self.email.strip().lower().encode("utf-8")
        ).hexdigest()
        return super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return "%s (%i) from %s" % (self.email, self.pk, self.user)


class UnconfirmedEmail(BaseAccountModel):
    """
    Model holding unconfirmed email addresses as well as the verification key
    """

    email = models.EmailField(max_length=MAX_LENGTH_EMAIL)
    verification_key = models.CharField(max_length=64)
    last_send_date = models.DateTimeField(null=True, blank=True)
    last_status = models.TextField(max_length=2047, null=True, blank=True)

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Class attributes
        """

        verbose_name = _("unconfirmed email")
        verbose_name_plural = _("unconfirmed emails")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.verification_key:
            hash_object = hashlib.new("sha256")
            hash_object.update(
                urandom(1024)
                + self.user.username.encode("utf-8")  # pylint: disable=no-member
            )  # pylint: disable=no-member
            self.verification_key = hash_object.hexdigest()
        super(UnconfirmedEmail, self).save(
            force_insert, force_update, using, update_fields
        )

    def send_confirmation_mail(self, url=SECURE_BASE_URL):
        """
        Send confirmation mail to that mail address
        """
        link = url + reverse(
            "confirm_email", kwargs={"verification_key": self.verification_key}
        )
        email_subject = _("Confirm your email address on %s") % SITE_NAME
        email_body = render_to_string(
            "email_confirmation.txt",
            {
                "verification_link": link,
                "site_name": SITE_NAME,
            },
        )
        self.last_send_date = timezone.now()
        self.last_status = "OK"
        # if settings.DEBUG:
        #    print('DEBUG: %s' % link)
        try:
            send_mail(email_subject, email_body, DEFAULT_FROM_EMAIL, [self.email])
        except Exception as e:
            self.last_status = f"{e}"
        self.save()
        return True

    def __str__(self):
        return "%s (%i) from %s" % (self.email, self.pk, self.user)


class UnconfirmedOpenId(BaseAccountModel):
    """
    Model holding unconfirmed OpenIDs
    """

    openid = models.URLField(unique=False, max_length=MAX_LENGTH_URL)

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Meta class
        """

        verbose_name = _("unconfirmed OpenID")
        verbose_name_plural = "unconfirmed_OpenIDs"

    def __str__(self):
        return "%s (%i) from %s" % (self.openid, self.pk, self.user)


class ConfirmedOpenId(BaseAccountModel):
    """
    Model holding confirmed OpenIDs, as well as the relation to
    the assigned photo
    """

    openid = models.URLField(unique=True, max_length=MAX_LENGTH_URL)
    photo = models.ForeignKey(
        Photo,
        related_name="openids",
        blank=True,
        null=True,
        on_delete=models.deletion.SET_NULL,
    )
    # http://<id>/ base version - http w/ trailing slash
    digest = models.CharField(max_length=64)
    # http://<id> - http w/o trailing slash
    alt_digest1 = models.CharField(max_length=64, null=True, blank=True, default=None)
    # https://<id>/ - https w/ trailing slash
    alt_digest2 = models.CharField(max_length=64, null=True, blank=True, default=None)
    # https://<id> - https w/o trailing slash
    alt_digest3 = models.CharField(max_length=64, null=True, blank=True, default=None)
    # Alternative assignment - use Bluesky handle
    bluesky_handle = models.CharField(max_length=256, null=True, blank=True)

    access_count = models.BigIntegerField(default=0, editable=False)

    class Meta:  # pylint: disable=too-few-public-methods
        """
        Meta class
        """

        verbose_name = _("confirmed OpenID")
        verbose_name_plural = _("confirmed OpenIDs")

    def set_photo(self, photo):
        """
        Helper method to save photo
        """
        self.photo = photo
        self.save()

    def set_bluesky_handle(self, handle):
        """
        Helper method to set Bluesky handle
        """
        bs = Bluesky()
        handle = bs.normalize_handle(handle)
        avatar = bs.get_profile(handle)
        if not avatar:
            raise Exception("Invalid Bluesky handle")
        self.bluesky_handle = handle
        self.save()

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        url = urlsplit(self.openid)
        if url.username:  # pragma: no cover
            password = url.password or ""
            netloc = f"{url.username}:{password}@{url.hostname}"
        else:
            netloc = url.hostname
        lowercase_url = urlunsplit(
            (url.scheme.lower(), netloc, url.path, url.query, url.fragment)
        )
        self.openid = lowercase_url

        self.digest = hashlib.sha256(
            openid_variations(lowercase_url)[0].encode("utf-8")
        ).hexdigest()
        self.alt_digest1 = hashlib.sha256(
            openid_variations(lowercase_url)[1].encode("utf-8")
        ).hexdigest()
        self.alt_digest2 = hashlib.sha256(
            openid_variations(lowercase_url)[2].encode("utf-8")
        ).hexdigest()
        self.alt_digest3 = hashlib.sha256(
            openid_variations(lowercase_url)[3].encode("utf-8")
        ).hexdigest()

        return super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return "%s (%i) (%s)" % (self.openid, self.pk, self.user)


class OpenIDNonce(models.Model):
    """
    Model holding OpenID Nonces
    See also: https://github.com/edx/django-openid-auth/
    """

    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=128)

    def __str__(self):
        return "%s (%i) (timestamp: %i)" % (self.server_url, self.pk, self.timestamp)


class OpenIDAssociation(models.Model):
    """
    Model holding the relation/association about OpenIDs
    """

    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255)  # stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)

    def __str__(self):
        return "%s (%i) (%s, lifetime: %i)" % (
            self.server_url,
            self.pk,
            self.assoc_type,
            self.lifetime,
        )


class DjangoOpenIDStore(OpenIDStore):
    """
    The Python openid library needs an OpenIDStore subclass to persist data
    related to OpenID authentications. This one uses our Django models.
    """

    @staticmethod
    def storeAssociation(server_url, association):  # pragma: no cover
        """
        Helper method to store associations
        """
        assoc = OpenIDAssociation(
            server_url=server_url,
            handle=association.handle,
            secret=base64.encodebytes(association.secret),
            issued=association.issued,
            lifetime=association.issued,
            assoc_type=association.assoc_type,
        )
        assoc.save()

    def getAssociation(self, server_url, handle=None):  # pragma: no cover
        """
        Helper method to get associations
        """
        assocs = []
        if handle is not None:
            assocs = OpenIDAssociation.objects.filter(  # pylint: disable=no-member
                server_url=server_url, handle=handle
            )
        else:
            assocs = OpenIDAssociation.objects.filter(  # pylint: disable=no-member
                server_url=server_url
            )
        if not assocs:
            return None
        associations = []
        for assoc in assocs:
            if isinstance(assoc.secret, str):
                assoc.secret = assoc.secret.split("b'")[1].split("'")[0]
                assoc.secret = bytes(assoc.secret, "utf-8")
            association = OIDAssociation(
                assoc.handle,
                base64.decodebytes(assoc.secret),
                assoc.issued,
                assoc.lifetime,
                assoc.assoc_type,
            )
            expires = 0
            try:
                # pylint: disable=no-member
                expires = association.getExpiresIn()
            except AttributeError:
                expires = association.expiresIn
            if expires == 0:
                self.removeAssociation(server_url, assoc.handle)
            else:
                associations.append((association.issued, association))
        return associations[-1][1] if associations else None

    @staticmethod
    def removeAssociation(server_url, handle):  # pragma: no cover
        """
        Helper method to remove associations
        """
        assocs = list(
            OpenIDAssociation.objects.filter(  # pylint: disable=no-member
                server_url=server_url, handle=handle
            )
        )
        assocs_exist = len(assocs) > 0
        for assoc in assocs:
            assoc.delete()
        return assocs_exist

    @staticmethod
    def useNonce(server_url, timestamp, salt):  # pragma: no cover
        """
        Helper method to 'use' nonces
        """
        # Has nonce expired?
        if abs(timestamp - time.time()) > oidnonce.SKEW:
            return False
        try:
            nonce = OpenIDNonce.objects.get(  # pylint: disable=no-member
                server_url__exact=server_url,
                timestamp__exact=timestamp,
                salt__exact=salt,
            )
        except ObjectDoesNotExist:
            nonce = OpenIDNonce.objects.create(  # pylint: disable=no-member
                server_url=server_url, timestamp=timestamp, salt=salt
            )
            return True
        nonce.delete()
        return False

    @staticmethod
    def cleanupNonces():  # pragma: no cover
        """
        Helper method to cleanup nonces
        """
        timestamp = int(time.time()) - oidnonce.SKEW
        # pylint: disable=no-member
        OpenIDNonce.objects.filter(timestamp__lt=timestamp).delete()

    @staticmethod
    def cleanupAssociations():  # pragma: no cover
        """
        Helper method to cleanup associations
        """
        OpenIDAssociation.objects.extra(
            where=[f"issued + lifetimeint < ({time.time()})"]
        ).delete()
