# -*- coding: utf-8 -*-
"""
Helper method to fetch Gravatar image
"""
from ssl import SSLError
from urllib.request import HTTPError, URLError
from ivatar.utils import urlopen
import hashlib

from ..settings import AVATAR_MAX_SIZE


def get_photo(email):
    """
    Fetch photo from Gravatar, given an email address
    """
    hash_object = hashlib.new("md5")
    hash_object.update(email.lower().encode("utf-8"))
    thumbnail_url = (
        "https://secure.gravatar.com/avatar/"
        + hash_object.hexdigest()
        + "?s=%i&d=404" % AVATAR_MAX_SIZE
    )
    image_url = (
        f"https://secure.gravatar.com/avatar/{hash_object.hexdigest()}?s=512&d=404"
    )

    # Will redirect to the public profile URL if it exists
    service_url = f"http://www.gravatar.com/{hash_object.hexdigest()}"

    try:
        urlopen(image_url)
    except HTTPError as exc:
        if exc.code not in [404, 503]:
            print(f"Gravatar fetch failed with an unexpected {exc.code} HTTP error")
        return False
    except URLError as exc:  # pragma: no cover
        print(f"Gravatar fetch failed with URL error: {exc.reason}")
        return False  # pragma: no cover
    except SSLError as exc:  # pragma: no cover
        print(f"Gravatar fetch failed with SSL error: {exc.reason}")
        return False  # pragma: no cover

    return {
        "thumbnail_url": thumbnail_url,
        "image_url": image_url,
        "width": AVATAR_MAX_SIZE,
        "height": AVATAR_MAX_SIZE,
        "service_url": service_url,
        "service_name": "Gravatar",
    }
