#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django
import timeit

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "ivatar.settings"
)  # pylint: disable=wrong-import-position
django.setup()  # pylint: disable=wrong-import-position

from ivatar.ivataraccount.models import ConfirmedEmail, APIKey
from simplecrypt import decrypt
from binascii import unhexlify

digest = None
digest_sha256 = None


def get_digest_sha256():
    digest_sha256 = ConfirmedEmail.objects.first().encrypted_digest_sha256(
        secret_key=APIKey.objects.first()
    )
    return digest_sha256


def get_digest():
    digest = ConfirmedEmail.objects.first().encrypted_digest(
        secret_key=APIKey.objects.first()
    )
    return digest


def decrypt_digest():
    return decrypt(APIKey.objects.first().secret_key, unhexlify(digest))


def decrypt_digest_256():
    return decrypt(APIKey.objects.first().secret_key, unhexlify(digest_sha256))


digest = get_digest()
digest_sha256 = get_digest_sha256()

print("Encrypt digest:        %s" % timeit.timeit(get_digest, number=1))
print("Encrypt digest_sha256: %s" % timeit.timeit(get_digest_sha256, number=1))
print("Decrypt digest:        %s" % timeit.timeit(decrypt_digest, number=1))
print("Decrypt digest_sha256: %s" % timeit.timeit(decrypt_digest_256, number=1))
