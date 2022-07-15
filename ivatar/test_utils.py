# -*- coding: utf-8 -*-
"""
Test our utils from ivatar.utils
"""

from django.test import TestCase

from ivatar.utils import is_trusted_url, openid_variations


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

    def test_is_trusted_url(self):
        test1 = is_trusted_url("https://gravatar.com/avatar/63a75a80e6b1f4adfdb04c1ca02e596c", [
            {
                "schemes": [
                    "http",
                    "https"
                ],
                "host_equals": "gravatar.com",
                "path_prefix": "/avatar/"
            }
        ])
        self.assertTrue(test1)

        test2 = is_trusted_url("https://gravatar.com.example.org/avatar/63a75a80e6b1f4adfdb04c1ca02e596c", [
            {
                "schemes": [
                    "http",
                    "https"
                ],
                "host_suffix": ".gravatar.com",
                "path_prefix": "/avatar/"
            }
        ])
        self.assertFalse(test2)

        # Test against open redirect with valid URL in query params
        test3 = is_trusted_url("https://github.com/SethFalco/?boop=https://secure.gravatar.com/avatar/205e460b479e2e5b48aec07710c08d50", [
            {
                "schemes": [
                    "http",
                    "https"
                ],
                "host_suffix": ".gravatar.com",
                "path_prefix": "/avatar/"
            }
        ])
        self.assertFalse(test3)

        test4 = is_trusted_url("https://ui-avatars.com/api/blah", [
            {
                "schemes": [
                    "https"
                ],
                "host_equals": "ui-avatars.com",
                "path_prefix": "/api/"
            },
            {
                "schemes": [
                    "http",
                    "https"
                ],
                "host_suffix": ".gravatar.com",
                "path_prefix": "/avatar/"
            }
        ])
        self.assertTrue(test4)
