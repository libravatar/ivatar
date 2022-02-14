# -*- coding: utf-8 -*-
"""
Test various other parts of ivatar/libravatar in order
to increase the overall test coverage. Test in here, didn't
fit anywhere else.
"""

from django.test import TestCase
from django.contrib.auth.models import User

from ivatar.utils import random_string
from ivatar.ivataraccount.models import pil_format, UserPreference


class Tester(TestCase):
    """
    Main test class
    """

    user = None
    username = random_string()

    def setUp(self):
        """
        Prepare tests.
        - Create user
        """
        self.user = User.objects.create_user(
            username=self.username,
        )

    def test_pil_format(self):
        """
        Test pil format function
        """
        self.assertEqual(pil_format("jpg"), "JPEG")
        self.assertEqual(pil_format("jpeg"), "JPEG")
        self.assertEqual(pil_format("png"), "PNG")
        self.assertEqual(pil_format("gif"), "GIF")
        self.assertEqual(pil_format("abc"), None)

    def test_userprefs_str(self):
        """
        Test if str representation of UserPreferences is as expected
        """
        up = UserPreference(theme="default", user=self.user)
        print(up)
