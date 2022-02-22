# -*- coding: utf-8 -*-
"""
Test our utils from ivatar.utils
"""

from django.test import TestCase

from ivatar.utils import openid_variations


class Tester(TestCase):
    """
    Main test class
    """

    def test_openid_variations(self):
        """
        Test if the OpenID variation "generator" does the correct thing
        """
        openid0 = "http://user.url/"
        openid1 = "http://user.url"
        openid2 = "https://user.url/"
        openid3 = "https://user.url"

        # First variation
        self.assertEqual(openid_variations(openid0)[0], openid0)
        self.assertEqual(openid_variations(openid0)[1], openid1)
        self.assertEqual(openid_variations(openid0)[2], openid2)
        self.assertEqual(openid_variations(openid0)[3], openid3)

        # Second varitations
        self.assertEqual(openid_variations(openid1)[0], openid0)
        self.assertEqual(openid_variations(openid1)[1], openid1)
        self.assertEqual(openid_variations(openid1)[2], openid2)
        self.assertEqual(openid_variations(openid1)[3], openid3)

        # Third varitations
        self.assertEqual(openid_variations(openid2)[0], openid0)
        self.assertEqual(openid_variations(openid2)[1], openid1)
        self.assertEqual(openid_variations(openid2)[2], openid2)
        self.assertEqual(openid_variations(openid2)[3], openid3)

        # Forth varitations
        self.assertEqual(openid_variations(openid3)[0], openid0)
        self.assertEqual(openid_variations(openid3)[1], openid1)
        self.assertEqual(openid_variations(openid3)[2], openid2)
        self.assertEqual(openid_variations(openid3)[3], openid3)
