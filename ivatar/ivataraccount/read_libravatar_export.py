# -*- coding: utf-8 -*-
"""
Reading libravatar export
"""

import binascii
import os
from io import BytesIO
import gzip
import xml.etree.ElementTree
import base64
from PIL import Image
import django
import sys

sys.path.append(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
    )
)

os.environ["DJANGO_SETTINGS_MODULE"] = "ivatar.settings"
django.setup()

# pylint: disable=wrong-import-position
from ivatar.settings import SCHEMAROOT


def read_gzdata(gzdata=None):
    """
    Read gzipped data file
    """
    photos = []  # pylint: disable=invalid-name
    username = None  # pylint: disable=invalid-name
    password = None  # pylint: disable=invalid-name

    if not gzdata:
        return False

    fh = gzip.open(BytesIO(gzdata), "rb")  # pylint: disable=invalid-name
    content = fh.read()
    fh.close()
    root = xml.etree.ElementTree.fromstring(content)
    if root.tag != "{%s}user" % SCHEMAROOT:
        print(f"Unknown export format: {root.tag}")
        exit(-1)

    # Username
    for item in root.findall("{%s}account" % SCHEMAROOT)[0].items():
        if item[0] == "username":
            username = item[1]
        if item[0] == "password":
            password = item[1]

    emails = [
        {"email": email.text, "photo_id": email.attrib["photo_id"]}
        for email in root.findall("{%s}emails" % SCHEMAROOT)[0]
        if email.tag == "{%s}email" % SCHEMAROOT
    ]
    openids = [
        {"openid": openid.text, "photo_id": openid.attrib["photo_id"]}
        for openid in root.findall("{%s}openids" % SCHEMAROOT)[0]
        if openid.tag == "{%s}openid" % SCHEMAROOT
    ]
    # Photos
    for photo in root.findall("{%s}photos" % SCHEMAROOT)[0]:
        if photo.tag == "{%s}photo" % SCHEMAROOT:
            try:
                # Safety measures to make sure we do not try to parse
                # a binary encoded string
                photo.text = photo.text.strip("'")
                photo.text = photo.text.strip("\\n")
                photo.text = photo.text.lstrip("b'")
                data = base64.decodebytes(bytes(photo.text, "utf-8"))
            except binascii.Error as exc:
                print(
                    f'Cannot decode photo; Encoding: {photo.attrib["encoding"]}, Format: {photo.attrib["format"]}, Id: {photo.attrib["id"]}: {exc}'
                )
                continue
            try:
                Image.open(BytesIO(data))
            except Exception as exc:  # pylint: disable=broad-except
                print(
                    f'Cannot decode photo; Encoding: {photo.attrib["encoding"]}, Format: {photo.attrib["format"]}, Id: {photo.attrib["id"]}: {exc}'
                )
                continue
            else:
                # If it is a working image, we can use it
                photo.text.replace("\n", "")
                photos.append(
                    {
                        "data": photo.text,
                        "format": photo.attrib["format"],
                        "id": photo.attrib["id"],
                    }
                )

    return {
        "emails": emails,
        "openids": openids,
        "photos": photos,
        "username": username,
        "password": password,
    }
