#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import a CSV - Format as follows:
    <mailaddr>,<path_to_image>

Example:
    myuser@mydomain.tld,myphoto.jpeg

This will create or update an existing user and assign the image
to the given address.
"""

import os
from os.path import isfile
import sys
from io import BytesIO
import csv
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "ivatar.settings"
)  # pylint: disable=wrong-import-position
django.setup()  # pylint: disable=wrong-import-position
from django.contrib.auth.models import User
from PIL import Image
from ivatar.settings import JPEG_QUALITY
from ivatar.ivataraccount.models import ConfirmedEmail
from ivatar.ivataraccount.models import Photo
from ivatar.ivataraccount.models import file_format

if len(sys.argv) < 2:
    print("First argument to '%s' must be the path to the CSV" % sys.argv[0])
    exit(-255)

if not isfile(sys.argv[1]):
    print("First argument to '%s' must be a path to the CSV" % sys.argv[0])
    exit(-255)

PATH = sys.argv[1]
with open(PATH, newline="") as csvfile:
    contactreader = csv.reader(csvfile, delimiter=",")
    for row in contactreader:
        mailaddr = row[0]
        image = row[1]

        if not isfile(image):
            print("File '%s' doesn't exist - cannot add" % image)
            continue

        print("Adding: %s" % mailaddr)

        (user, created) = User.objects.get_or_create(username=mailaddr)
        if not user.confirmedemail_set.count() < 1:
            ConfirmedEmail.objects.get_or_create(
                email=mailaddr,
                user=user,
            )
        user.save()
        with open(image, "rb") as avatar:
            pilobj = Image.open(avatar)
            out = BytesIO()
            pilobj.save(out, pilobj.format, quality=JPEG_QUALITY)
            out.seek(0)
            photo = None
            if user.photo_set.count() < 1:
                photo = Photo()
                photo.user = user
            else:
                photo = user.photo_set.first()
            photo.ip_address = "0.0.0.0"
            photo.format = file_format(pilobj.format)
            photo.data = out.read()
            photo.save()
            print("xxx: %s" % user.confirmedemail_set.first())
            confirmed_email = user.confirmedemail_set.first()
            confirmed_email.photo_id = photo.id
            confirmed_email.save()
