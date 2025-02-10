# -*- coding: utf-8 -*-
"""
views under /
"""

import contextlib
from io import BytesIO
from os import path
import hashlib
from ivatar.utils import urlopen, Bluesky
from urllib.error import HTTPError, URLError
from ssl import SSLError
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseNotFound, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache, caches
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.models import User

from PIL import Image

from monsterid.id import build_monster as BuildMonster
import Identicon
from pydenticon5 import Pydenticon5
import pagan
from robohash import Robohash

from ivatar.settings import AVATAR_MAX_SIZE, JPEG_QUALITY, DEFAULT_AVATAR_SIZE
from ivatar.settings import CACHE_RESPONSE
from ivatar.settings import CACHE_IMAGES_MAX_AGE
from ivatar.settings import TRUSTED_DEFAULT_URLS
from .ivataraccount.models import ConfirmedEmail, ConfirmedOpenId
from .ivataraccount.models import UnconfirmedEmail, UnconfirmedOpenId
from .ivataraccount.models import Photo
from .ivataraccount.models import pil_format, file_format
from .utils import is_trusted_url, mm_ng, resize_animated_gif


def get_size(request, size=DEFAULT_AVATAR_SIZE):
    """
    Get size from the URL arguments
    """
    sizetemp = None
    if "s" in request.GET:
        sizetemp = request.GET["s"]
    if "size" in request.GET:
        sizetemp = request.GET["size"]
    if sizetemp:
        if sizetemp not in ["", "0"]:
            with contextlib.suppress(ValueError):
                if int(sizetemp) > 0:
                    size = int(sizetemp)
    size = min(size, int(AVATAR_MAX_SIZE))
    return size


class CachingHttpResponse(HttpResponse):
    """
    Handle caching of response
    """

    def __init__(
        self,
        uri,
        content=b"",
        content_type=None,
        status=200,  # pylint: disable=too-many-arguments
        reason=None,
        charset=None,
    ):
        if CACHE_RESPONSE:
            caches["filesystem"].set(
                uri,
                {
                    "content": content,
                    "content_type": content_type,
                    "status": status,
                    "reason": reason,
                    "charset": charset,
                },
            )
        super().__init__(content, content_type, status, reason, charset)


class AvatarImageView(TemplateView):
    """
    View to return (binary) image, based on OpenID/Email (both by digest)
    """

    # TODO: Do cache resize images!! Memcached?

    def options(self, request, *args, **kwargs):
        response = HttpResponse("", content_type="text/plain")
        response["Allow"] = "404 mm mp retro pagan wavatar monsterid robohash identicon"
        return response

    def get(
        self, request, *args, **kwargs
    ):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-return-statements
        """
        Override get from parent class
        """
        model = ConfirmedEmail
        size = get_size(request)
        imgformat = "png"
        obj = None
        default = None
        forcedefault = False
        gravatarredirect = False
        gravatarproxy = True
        uri = request.build_absolute_uri()

        # Check the cache first
        if CACHE_RESPONSE:
            if centry := caches["filesystem"].get(uri):
                # For DEBUG purpose only
                # print('Cached entry for %s' % uri)
                return HttpResponse(
                    centry["content"],
                    content_type=centry["content_type"],
                    status=centry["status"],
                    reason=centry["reason"],
                    charset=centry["charset"],
                )

        # In case no digest at all is provided, return to home page
        if "digest" not in kwargs:
            return HttpResponseRedirect(reverse_lazy("home"))

        if "d" in request.GET:
            default = request.GET["d"]
        if "default" in request.GET:
            default = request.GET["default"]

        if default is not None:
            if TRUSTED_DEFAULT_URLS is None:
                print("Query parameter `default` is disabled.")
                default = None
            elif default.find("://") > 0:
                # Check if it's trusted, if not, reset to None
                trusted_url = is_trusted_url(default, TRUSTED_DEFAULT_URLS)

                if not trusted_url:
                    print(
                        f"Default URL is not in trusted URLs: '{default}'; Kicking it!"
                    )
                    default = None

        if "f" in request.GET:
            if request.GET["f"] == "y":
                forcedefault = True
        if "forcedefault" in request.GET:
            if request.GET["forcedefault"] == "y":
                forcedefault = True

        if "gravatarredirect" in request.GET:
            if request.GET["gravatarredirect"] == "y":
                gravatarredirect = True

        if "gravatarproxy" in request.GET:
            if request.GET["gravatarproxy"] == "n":
                gravatarproxy = False

        try:
            obj = model.objects.get(digest=kwargs["digest"])
        except ObjectDoesNotExist:
            try:
                obj = model.objects.get(digest_sha256=kwargs["digest"])
            except ObjectDoesNotExist:
                model = ConfirmedOpenId
                with contextlib.suppress(Exception):
                    d = kwargs["digest"]  # pylint: disable=invalid-name
                    # OpenID is tricky. http vs. https, versus trailing slash or not
                    # However, some users eventually have added their variations already
                    # and therefore we need to use filter() and first()
                    obj = model.objects.filter(
                        Q(digest=d)
                        | Q(alt_digest1=d)
                        | Q(alt_digest2=d)
                        | Q(alt_digest3=d)
                    ).first()
        # Handle the special case of Bluesky
        if obj:
            if obj.bluesky_handle:
                return HttpResponseRedirect(
                    reverse_lazy("blueskyproxy", args=[kwargs["digest"]])
                )
        # If that mail/openid doesn't exist, or has no photo linked to it
        if not obj or not obj.photo or forcedefault:
            gravatar_url = (
                "https://secure.gravatar.com/avatar/"
                + kwargs["digest"]
                + "?s=%i" % size
            )

            # If we have redirection to Gravatar enabled, this overrides all
            # default= settings, except forcedefault!
            if gravatarredirect and not forcedefault:
                return HttpResponseRedirect(gravatar_url)

            # Request to proxy Gravatar image - only if not forcedefault
            if gravatarproxy and not forcedefault:
                url = (
                    reverse_lazy("gravatarproxy", args=[kwargs["digest"]])
                    + "?s=%i" % size
                )
                # Ensure we do not convert None to string 'None'
                if default:
                    url += f"&default={default}"
                return HttpResponseRedirect(url)

            # Return the default URL, as specified, or 404 Not Found, if default=404
            if default:
                # Proxy to gravatar to generate wavatar - lazy me
                if str(default) == "wavatar":
                    url = (
                        reverse_lazy("gravatarproxy", args=[kwargs["digest"]])
                        + "?s=%i" % size
                        + f"&default={default}&f=y"
                    )
                    return HttpResponseRedirect(url)

                if str(default) == str(404):
                    return HttpResponseNotFound(_("<h1>Image not found</h1>"))

                if str(default) == "monsterid":
                    monsterdata = BuildMonster(seed=kwargs["digest"], size=(size, size))
                    data = BytesIO()
                    return self._return_cached_png(monsterdata, data, uri)
                if str(default) == "robohash":
                    roboset = request.GET.get("robohash") or "any"
                    robohash = Robohash(kwargs["digest"])
                    robohash.assemble(roboset=roboset, sizex=size, sizey=size)
                    data = BytesIO()
                    robohash.img.save(data, format="png")
                    return self._return_cached_response(data, uri)
                if str(default) == "retro":
                    identicon = Identicon.render(kwargs["digest"])
                    data = BytesIO()
                    img = Image.open(BytesIO(identicon))
                    img = img.resize((size, size), Image.LANCZOS)
                    return self._return_cached_png(img, data, uri)
                if str(default) == "pagan":
                    paganobj = pagan.Avatar(kwargs["digest"])
                    data = BytesIO()
                    img = paganobj.img.resize((size, size), Image.LANCZOS)
                    return self._return_cached_png(img, data, uri)
                if str(default) == "identicon":
                    p = Pydenticon5()  # pylint: disable=invalid-name
                    # In order to make use of the whole 32 bytes digest, we need to redigest them.
                    newdigest = hashlib.md5(
                        bytes(kwargs["digest"], "utf-8")
                    ).hexdigest()
                    img = p.draw(newdigest, size, 0)
                    data = BytesIO()
                    return self._return_cached_png(img, data, uri)
                if str(default) == "mmng":
                    mmngimg = mm_ng(idhash=kwargs["digest"], size=size)
                    data = BytesIO()
                    return self._return_cached_png(mmngimg, data, uri)
                if str(default) in {"mm", "mp"}:
                    return self._redirect_static_w_size("mm", size)
                return HttpResponseRedirect(default)

            return self._redirect_static_w_size("nobody", size)
        imgformat = obj.photo.format
        photodata = Image.open(BytesIO(obj.photo.data))

        data = BytesIO()

        # Animated GIFs need additional handling
        if imgformat == "gif" and photodata.is_animated:
            # Debug only
            # print("Object is animated and has %i frames" % photodata.n_frames)
            data = resize_animated_gif(photodata, (size, size))
        else:
            # If the image is smaller than what was requested, we need
            # to use the function resize
            if photodata.size[0] < size or photodata.size[1] < size:
                photodata = photodata.resize((size, size), Image.LANCZOS)
            else:
                photodata.thumbnail((size, size), Image.LANCZOS)
            photodata.save(data, pil_format(imgformat), quality=JPEG_QUALITY)

        data.seek(0)
        obj.photo.access_count += 1
        obj.photo.save()
        obj.access_count += 1
        obj.save()
        if imgformat == "jpg":
            imgformat = "jpeg"
        response = CachingHttpResponse(uri, data, content_type=f"image/{imgformat}")
        response["Cache-Control"] = "max-age=%i" % CACHE_IMAGES_MAX_AGE
        return response

    def _redirect_static_w_size(self, arg0, size):
        """
        Helper method to redirect to static image with size i/a
        """
        # If mm is explicitly given, we need to catch that
        static_img = path.join("static", "img", arg0, f"{str(size)}.png")
        if not path.isfile(static_img):
            # We trust this exists!!!
            static_img = path.join("static", "img", arg0, "512.png")
        # We trust static/ is mapped to /static/
        return HttpResponseRedirect(f"/{static_img}")

    def _return_cached_response(self, data, uri):
        data.seek(0)
        response = CachingHttpResponse(uri, data, content_type="image/png")
        response["Cache-Control"] = "max-age=%i" % CACHE_IMAGES_MAX_AGE
        return response

    def _return_cached_png(self, arg0, data, uri):
        arg0.save(data, "PNG", quality=JPEG_QUALITY)
        return self._return_cached_response(data, uri)


class GravatarProxyView(View):
    """
    Proxy request to Gravatar and return the image from there
    """

    # TODO: Do cache images!! Memcached?

    def get(
        self, request, *args, **kwargs
    ):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals,no-self-use,unused-argument,too-many-return-statements
        """
        Override get from parent class
        """

        def redir_default(default=None):
            url = (
                reverse_lazy("avatar_view", args=[kwargs["digest"]])
                + "?s=%i" % size
                + "&forcedefault=y"
            )
            if default is not None:
                url += f"&default={default}"
            return HttpResponseRedirect(url)

        size = get_size(request)
        gravatarimagedata = None
        default = None

        with contextlib.suppress(Exception):
            if str(request.GET["default"]) != "None":
                default = request.GET["default"]
        if str(default) != "wavatar":
            # This part is special/hackish
            # Check if the image returned by Gravatar is their default image, if so,
            # redirect to our default instead.
            gravatar_test_url = (
                "https://secure.gravatar.com/avatar/"
                + kwargs["digest"]
                + "?s=%i&d=%i" % (50, 404)
            )
            if cache.get(gravatar_test_url) == "default":
                # DEBUG only
                # print("Cached Gravatar response: Default.")
                return redir_default(default)
            try:
                urlopen(gravatar_test_url)
            except HTTPError as exc:
                if exc.code == 404:
                    cache.set(gravatar_test_url, "default", 60)
                else:
                    print(f"Gravatar test url fetch failed: {exc}")
                return redir_default(default)

        gravatar_url = (
            "https://secure.gravatar.com/avatar/" + kwargs["digest"] + "?s=%i" % size
        )
        if default:
            gravatar_url += f"&d={default}"

        try:
            if cache.get(gravatar_url) == "err":
                print(f"Cached Gravatar fetch failed with URL error: {gravatar_url}")
                return redir_default(default)

            gravatarimagedata = urlopen(gravatar_url)
        except HTTPError as exc:
            if exc.code not in [404, 503]:
                print(
                    f"Gravatar fetch failed with an unexpected {exc.code} HTTP error: {gravatar_url}"
                )
            cache.set(gravatar_url, "err", 30)
            return redir_default(default)
        except URLError as exc:
            print(f"Gravatar fetch failed with URL error: {exc.reason}")
            cache.set(gravatar_url, "err", 30)
            return redir_default(default)
        except SSLError as exc:
            print(f"Gravatar fetch failed with SSL error: {exc.reason}")
            cache.set(gravatar_url, "err", 30)
            return redir_default(default)
        try:
            data = BytesIO(gravatarimagedata.read())
            img = Image.open(data)
            data.seek(0)
            response = HttpResponse(
                data.read(), content_type=f"image/{file_format(img.format)}"
            )
            response["Cache-Control"] = "max-age=%i" % CACHE_IMAGES_MAX_AGE
            return response

        except ValueError as exc:
            print(f"Value error: {exc}")
            return redir_default(default)

        # We shouldn't reach this point... But make sure we do something
        return redir_default(default)


class BlueskyProxyView(View):
    """
    Proxy request to Bluesky and return the image from there
    """

    def get(
        self, request, *args, **kwargs
    ):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals,no-self-use,unused-argument,too-many-return-statements
        """
        Override get from parent class
        """

        def redir_default(default=None):
            url = (
                reverse_lazy("avatar_view", args=[kwargs["digest"]])
                + "?s=%i" % size
                + "&forcedefault=y"
            )
            if default is not None:
                url += f"&default={default}"
            return HttpResponseRedirect(url)

        size = get_size(request)
        print(size)
        blueskyimagedata = None
        default = None

        with contextlib.suppress(Exception):
            if str(request.GET["default"]) != "None":
                default = request.GET["default"]
        identity = None

        # First check for email, as this is the most common
        try:
            identity = ConfirmedEmail.objects.filter(
                Q(digest=kwargs["digest"]) | Q(digest_sha256=kwargs["digest"])
            ).first()
        except Exception as exc:
            print(exc)

        # If no identity is found in the email table, try the openid table
        if not identity:
            try:
                identity = ConfirmedOpenId.objects.filter(
                    Q(digest=kwargs["digest"])
                    | Q(alt_digest1=kwargs["digest"])
                    | Q(alt_digest2=kwargs["digest"])
                    | Q(alt_digest3=kwargs["digest"])
                ).first()
            except Exception as exc:
                print(exc)

        # If still no identity is found, redirect to the default
        if not identity:
            return redir_default(default)

        bs = Bluesky()
        bluesky_url = None
        # Try with the cache first
        with contextlib.suppress(Exception):
            if cache.get(identity.bluesky_handle):
                bluesky_url = cache.get(identity.bluesky_handle)
        if not bluesky_url:
            try:
                bluesky_url = bs.get_avatar(identity.bluesky_handle)
                cache.set(identity.bluesky_handle, bluesky_url)
            except Exception:  # pylint: disable=bare-except
                return redir_default(default)

        try:
            if cache.get(bluesky_url) == "err":
                print(f"Cached Bluesky fetch failed with URL error: {bluesky_url}")
                return redir_default(default)

            blueskyimagedata = urlopen(bluesky_url)
        except HTTPError as exc:
            if exc.code not in [404, 503]:
                print(
                    f"Bluesky fetch failed with an unexpected {exc.code} HTTP error: {bluesky_url}"
                )
            cache.set(bluesky_url, "err", 30)
            return redir_default(default)
        except URLError as exc:
            print(f"Bluesky fetch failed with URL error: {exc.reason}")
            cache.set(bluesky_url, "err", 30)
            return redir_default(default)
        except SSLError as exc:
            print(f"Bluesky fetch failed with SSL error: {exc.reason}")
            cache.set(bluesky_url, "err", 30)
            return redir_default(default)
        try:
            data = BytesIO(blueskyimagedata.read())
            img = Image.open(data)
            img_format = img.format
            if max(img.size) > size:
                aspect = img.size[0] / float(img.size[1])
                if aspect > 1:
                    new_size = (size, int(size / aspect))
                else:
                    new_size = (int(size * aspect), size)
                img = img.resize(new_size)
            data = BytesIO()
            img.save(data, format=img_format)

            data.seek(0)
            response = HttpResponse(
                data.read(), content_type=f"image/{file_format(format)}"
            )
            response["Cache-Control"] = "max-age=%i" % CACHE_IMAGES_MAX_AGE
            return response
        except ValueError as exc:
            print(f"Value error: {exc}")
            return redir_default(default)

        # We shouldn't reach this point... But make sure we do something
        return redir_default(default)


class StatsView(TemplateView, JsonResponse):
    """
    Return stats
    """

    def get(
        self, request, *args, **kwargs
    ):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals,no-self-use,unused-argument,too-many-return-statements
        retval = {
            "users": User.objects.count(),
            "mails": ConfirmedEmail.objects.count(),
            "openids": ConfirmedOpenId.objects.count(),  # pylint: disable=no-member
            "unconfirmed_mails": UnconfirmedEmail.objects.count(),  # pylint: disable=no-member
            "unconfirmed_openids": UnconfirmedOpenId.objects.count(),  # pylint: disable=no-member
            "avatars": Photo.objects.count(),  # pylint: disable=no-member
        }

        return JsonResponse(retval)
