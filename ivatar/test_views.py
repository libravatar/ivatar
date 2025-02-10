# -*- coding: utf-8 -*-
"""
Test our views in ivatar.ivataraccount.views and ivatar.views
"""

import contextlib

# pylint: disable=too-many-lines
import os
import json
import django
from django.urls import reverse
from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User
from ivatar.utils import random_string, Bluesky

BLUESKY_APP_PASSWORD = None
BLUESKY_IDENTIFIER = None
with contextlib.suppress(Exception):
    from settings import BLUESKY_APP_PASSWORD, BLUESKY_IDENTIFIER
os.environ["DJANGO_SETTINGS_MODULE"] = "ivatar.settings"
django.setup()


class Tester(TestCase):  # pylint: disable=too-many-public-methods
    """
    Main test class
    """

    client = Client()
    user = None
    username = random_string()
    password = random_string()
    email = "%s@%s.%s" % (username, random_string(), random_string(2))
    # Dunno why random tld doesn't work, but I'm too lazy now to investigate
    openid = "http://%s.%s.%s/" % (username, random_string(), "org")

    def login(self):
        """
        Login as user
        """
        self.client.login(username=self.username, password=self.password)

    def setUp(self):
        """
        Prepare for tests.
        - Create user
        """
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )

    def test_incorrect_digest(self):
        """
        Test incorrect digest
        """
        response = self.client.get("/avatar/" + "x" * 65, follow=True)
        self.assertEqual(
            response.redirect_chain[2][0],
            "/static/img/nobody/80.png",
            "Doesn't redirect to static?",
        )
        # self.assertRedirects(
        #   response=response,
        #   expected_url="/static/img/nobody/80.png",
        #   msg_prefix="Why does an invalid hash not redirect to deadbeef?",
        # )

    def test_stats(self):
        """
        Test incorrect digest
        """
        response = self.client.get("/stats/", follow=True)
        self.assertEqual(response.status_code, 200, "unable to fetch stats!")
        j = json.loads(response.content)
        self.assertEqual(j["users"], 1, "user count incorrect")
        self.assertEqual(j["mails"], 0, "mails count incorrect")
        self.assertEqual(j["openids"], 0, "openids count incorrect")
        self.assertEqual(j["unconfirmed_mails"], 0, "unconfirmed mails count incorrect")
        self.assertEqual(
            j["unconfirmed_openids"], 0, "unconfirmed openids count incorrect"
        )
        self.assertEqual(j["avatars"], 0, "avatars count incorrect")

    def test_logout(self):
        """
        Test if logout works correctly
        """
        self.login()
        response = self.client.get(reverse("logout"), follow=True)
        self.assertEqual(
            response.status_code, 405, "logout with get should lead to http error 405"
        )
        response = self.client.post(reverse("logout"), follow=True)
        self.assertEqual(response.status_code, 200, "logout with post should logout")

    def test_Bluesky_client(self):
        """
        Bluesky client needs credentials, so it's limited with testing here now
        """

        if BLUESKY_APP_PASSWORD and BLUESKY_IDENTIFIER:
            b = Bluesky()
            profile = b.get_profile("ofalk.bsky.social")
            self.assertEqual(profile["handle"], "ofalk.bsky.social")
            # As long as I don't change my avatar, this should stay the same
            self.assertEqual(
                profile["avatar"],
                "https://cdn.bsky.app/img/avatar/plain/did:plc:35jdu26cjgsc5vdbsaqiuw4a/bafkreidgtubihcdwcr72s5nag2ohcnwhhbg2zabw4jtxlhmtekrm6t5f4y@jpeg",
            )
        self.assertEqual(True, True)
