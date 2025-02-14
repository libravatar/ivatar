# -*- coding: utf-8 -*-
"""
Configuration overrides for settings.py
"""

import os
import sys
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.messages import constants as message_constants
from ivatar.settings import BASE_DIR

from ivatar.settings import MIDDLEWARE
from ivatar.settings import INSTALLED_APPS
from ivatar.settings import TEMPLATES

ADMIN_USERS = []
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS.extend(
    [
        "django_extensions",
        "django_openid_auth",
        "bootstrap4",
        "anymail",
        "ivatar",
        "ivatar.ivataraccount",
        "ivatar.tools",
    ]
)

MIDDLEWARE.extend(
    [
        "django.middleware.locale.LocaleMiddleware",
    ]
)
MIDDLEWARE.insert(
    0,
    "ivatar.middleware.MultipleProxyMiddleware",
)

AUTHENTICATION_BACKENDS = (
    # Enable this to allow LDAP authentication.
    # See INSTALL for more information.
    # 'django_auth_ldap.backend.LDAPBackend',
    "django_openid_auth.auth.OpenIDBackend",
    "django.contrib.auth.backends.ModelBackend",
)

TEMPLATES[0]["DIRS"].extend(
    [
        os.path.join(BASE_DIR, "templates"),
    ]
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "ivatar.context_processors.basepage",
)

OPENID_CREATE_USERS = True
OPENID_UPDATE_DETAILS_FROM_SREG = True

SITE_NAME = os.environ.get("SITE_NAME", "libravatar")
IVATAR_VERSION = "1.7.0"

SCHEMAROOT = "https://www.libravatar.org/schemas/export/0.2"

SECURE_BASE_URL = os.environ.get(
    "SECURE_BASE_URL", "https://avatars.linux-kernel.at/avatar/"
)
BASE_URL = os.environ.get("BASE_URL", "http://avatars.linux-kernel.at/avatar/")

LOGIN_REDIRECT_URL = reverse_lazy("profile")
MAX_LENGTH_EMAIL = 254  # http://stackoverflow.com/questions/386294

MAX_NUM_PHOTOS = 5
MAX_NUM_UNCONFIRMED_EMAILS = 5
MAX_PHOTO_SIZE = 10485760  # in bytes
MAX_PIXELS = 7000
AVATAR_MAX_SIZE = 512
JPEG_QUALITY = 85

# I'm not 100% sure if single character domains are possible
# under any tld... so MIN_LENGTH_EMAIL/_URL, might be +1
MIN_LENGTH_URL = 11  # eg. http://a.io
MAX_LENGTH_URL = 255  # MySQL can't handle more than that (LP: 1018682)
MIN_LENGTH_EMAIL = 6  # eg. x@x.xx
MAX_LENGTH_EMAIL = 254  # http://stackoverflow.com/questions/386294

BOOTSTRAP4 = {
    "include_jquery": False,
    "javascript_in_head": False,
    "css_url": {
        "href": "/static/css/bootstrap.min.css",
        "integrity": "sha384-WskhaSGFgHYWDcbwN70/dfYBj47jz9qbsMId/iRN3ewGhXQFZCSftd1LZCfmhktB",
        "crossorigin": "anonymous",
    },
    "javascript_url": {
        "url": "/static/js/bootstrap.min.js",
        "integrity": "",
        "crossorigin": "anonymous",
    },
    "popper_url": {
        "url": "/static/js/popper.min.js",
        "integrity": "sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49",
        "crossorigin": "anonymous",
    },
}

if "EMAIL_BACKEND" in os.environ:
    EMAIL_BACKEND = os.environ["EMAIL_BACKEND"]  # pragma: no cover
else:
    if "test" in sys.argv or "collectstatic" in sys.argv:
        EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    else:
        try:
            ANYMAIL = {  # pragma: no cover
                "MAILGUN_API_KEY": os.environ["IVATAR_MAILGUN_API_KEY"],
                "MAILGUN_SENDER_DOMAIN": os.environ["IVATAR_MAILGUN_SENDER_DOMAIN"],
            }
            EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"  # pragma: no cover
        except Exception:  # pragma: nocover  # pylint: disable=broad-except
            EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "ivatar@mg.linux-kernel.at")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "ivatar@mg.linux-kernel.at")

try:
    from ivatar.settings import DATABASES
except ImportError:  # pragma: no cover
    DATABASES = []  # pragma: no cover

if "default" not in DATABASES:
    DATABASES["default"] = {  # pragma: no cover
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }

if "MYSQL_DATABASE" in os.environ:
    DATABASES["default"] = {  # pragma: no cover
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ["MYSQL_DATABASE"],
        "USER": os.environ["MYSQL_USER"],
        "PASSWORD": os.environ["MYSQL_PASSWORD"],
        "HOST": "mysql",
    }

if "POSTGRESQL_DATABASE" in os.environ:
    DATABASES["default"] = {  # pragma: no cover
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRESQL_DATABASE"],
        "USER": os.environ["POSTGRESQL_USER"],
        "PASSWORD": os.environ["POSTGRESQL_PASSWORD"],
        "HOST": "postgresql",
    }

SESSION_SERIALIZER = "django.contrib.sessions.serializers.PickleSerializer"

USE_X_FORWARDED_HOST = True
ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS = [
    "avatars.linux-kernel.at",
    "localhost",
]

DEFAULT_AVATAR_SIZE = 80

LANGUAGES = (
    ("de", _("Deutsch")),
    ("en", _("English")),
    ("ca", _("Català")),
    ("cs", _("Česky")),
    ("es", _("Español")),
    ("eu", _("Basque")),
    ("fr", _("Français")),
    ("it", _("Italiano")),
    ("ja", _("日本語")),
    ("nl", _("Nederlands")),
    ("pt", _("Português")),
    ("ru", _("Русский")),
    ("sq", _("Shqip")),
    ("tr", _("Türkçe")),
    ("uk", _("Українська")),
)

MESSAGE_TAGS = {
    message_constants.DEBUG: "debug",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": [
            "127.0.0.1:11211",
        ],
    },
    "filesystem": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/var/tmp/ivatar_cache",
        "TIMEOUT": 900,  # 15 minutes
    },
}

# This is 5 minutes caching for generated/resized images,
# so the sites don't hit ivatar so much - it's what's set in the HTTP header
CACHE_IMAGES_MAX_AGE = 5 * 60

CACHE_RESPONSE = True

# Trusted URLs for default redirection
TRUSTED_DEFAULT_URLS = [
    {"schemes": ["https"], "host_equals": "ui-avatars.com", "path_prefix": "/api/"},
    {
        "schemes": ["http", "https"],
        "host_equals": "gravatar.com",
        "path_prefix": "/avatar/",
    },
    {
        "schemes": ["http", "https"],
        "host_suffix": ".gravatar.com",
        "path_prefix": "/avatar/",
    },
    {
        "schemes": ["http", "https"],
        "host_equals": "www.gravatar.org",
        "path_prefix": "/avatar/",
    },
    {
        "schemes": ["https"],
        "host_equals": "avatars.dicebear.com",
        "path_prefix": "/api/",
    },
    {
        "schemes": ["https"],
        "host_equals": "badges.fedoraproject.org",
        "path_prefix": "/static/img/",
    },
    {
        "schemes": ["http"],
        "host_equals": "www.planet-libre.org",
        "path_prefix": "/themes/planetlibre/images/",
    },
    {"schemes": ["https"], "host_equals": "www.azuracast.com", "path_prefix": "/img/"},
    {
        "schemes": ["https"],
        "host_equals": "reps.mozilla.org",
        "path_prefix": "/static/base/img/remo/",
    },
]

# This MUST BE THE LAST!
if os.path.isfile(os.path.join(BASE_DIR, "config_local.py")):
    from config_local import *  # noqa # flake8: noqa # NOQA # pragma: no cover


def map_legacy_config(trusted_url):
    """
    For backward compability with the legacy configuration
    for trusting URLs. Adapts them to fit the new config.
    """
    if isinstance(trusted_url, str):
        return {"url_prefix": trusted_url}

    return trusted_url


# Backward compability for legacy behavior
TRUSTED_DEFAULT_URLS = list(map(map_legacy_config, TRUSTED_DEFAULT_URLS))
