# -*- coding: utf-8 -*-
"""
Simple module providing reusable random_string function
"""
import random
import string
from PIL import Image, ImageDraw


def random_string(length=10):
    """
    Return some random string with default length 10
    """
    return "".join(
        random.SystemRandom().choice(string.ascii_lowercase + string.digits)
        for _ in range(length)
    )


def openid_variations(openid):
    """
    Return the various OpenID variations, ALWAYS in the same order:
    - http w/ trailing slash
    - http w/o trailing slash
    - https w/ trailing slash
    - https w/o trailing slash
    """

    # Make the 'base' version: http w/ trailing slash
    if openid.startswith("https://"):
        openid = openid.replace("https://", "http://")
    if openid[-1] != "/":
        openid = openid + "/"

    # http w/o trailing slash
    var1 = openid[0:-1]
    var2 = openid.replace("http://", "https://")
    var3 = var2[0:-1]
    return (openid, var1, var2, var3)


def mm_ng(
    idhash, size=80, add_red=0, add_green=0, add_blue=0
):  # pylint: disable=too-many-locals
    """
    Return an MM (mystery man) image, based on a given hash
    add some red, green or blue, if specified
    """

    # Make sure the lightest bg color we paint is e0, else
    # we do not see the MM any more
    if idhash[0] == "f":
        idhash = "e0"

    # How large is the circle?
    circlesize = size * 0.6

    # Coordinates for the circle
    start_x = int(size * 0.2)
    end_x = start_x + circlesize
    start_y = int(size * 0.05)
    end_y = start_y + circlesize

    # All are the same, based on the input hash
    # this should always result in a "gray-ish" background
    red = idhash[0:2]
    green = idhash[0:2]
    blue = idhash[0:2]

    # Add some red (i/a) and make sure it's not over 255
    red = hex(int(red, 16) + add_red).replace("0x", "")
    if int(red, 16) > 255:
        red = "ff"
    if len(red) == 1:
        red = "0%s" % red

    # Add some green (i/a) and make sure it's not over 255
    green = hex(int(green, 16) + add_green).replace("0x", "")
    if int(green, 16) > 255:
        green = "ff"
    if len(green) == 1:
        green = "0%s" % green

    # Add some blue (i/a) and make sure it's not over 255
    blue = hex(int(blue, 16) + add_blue).replace("0x", "")
    if int(blue, 16) > 255:
        blue = "ff"
    if len(blue) == 1:
        blue = "0%s" % blue

    # Assemable the bg color "string" in webnotation. Eg. '#d3d3d3'
    bg_color = "#" + red + green + blue

    # Image
    image = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(image)

    # Draw background
    draw.rectangle(((0, 0), (size, size)), fill=bg_color)

    # Draw MMs head
    draw.ellipse((start_x, start_y, end_x, end_y), fill="white")

    # Draw MMs 'body'
    draw.polygon(
        (
            (start_x + circlesize / 2, size / 2.5),
            (size * 0.15, size),
            (size - size * 0.15, size),
        ),
        fill="white",
    )

    return image
