# -*- coding: utf-8 -*-
"""
Test our views in ivatar.ivataraccount.views and ivatar.views
"""

import contextlib

# pylint: disable=too-many-lines
import os
import django
from django.test import TestCase
from django.test import Client

from django.urls import reverse
from django.contrib.auth.models import User

# from django.contrib.auth import authenticate

os.environ["DJANGO_SETTINGS_MODULE"] = "ivatar.settings"
django.setup()

# pylint: disable=wrong-import-position
from ivatar import settings
from ivatar.ivataraccount.models import ConfirmedOpenId, ConfirmedEmail
from ivatar.utils import random_string

from libravatar import libravatar_url


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
    first_name = random_string()
    last_name = random_string()
    bsky_test_account = "ofalk.bsky.social"

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
            first_name=self.first_name,
            last_name=self.last_name,
        )
        settings.EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

    def create_confirmed_openid(self):
        """
        Create a confirmed openid
        """
        return ConfirmedOpenId.objects.create(
            user=self.user,
            ip_address="127.0.0.1",
            openid=self.openid,
        )

    def create_confirmed_email(self):
        """
        Create a confirmed email
        """
        return ConfirmedEmail.objects.create(
            email=self.email,
            user=self.user,
        )

    # The following tests need to be moved over to the model tests
    # and real web UI tests added
    def test_bluesky_handle_for_mail_via_model_handle_does_not_exist(self):
        """
        Add Bluesky handle to a confirmed mail address
        """
        self.login()
        confirmed = self.create_confirmed_email()
        confirmed.set_bluesky_handle(self.bsky_test_account)

        with contextlib.suppress(Exception):
            confirmed.set_bluesky_handle(f"{self.bsky_test_account}1")
        self.assertNotEqual(
            confirmed.bluesky_handle,
            f"{self.bsky_test_account}1",
            "Setting Bluesky handle that doesn't exist works?",
        )

    def test_bluesky_handle_for_mail_via_model_handle_exists(self):
        """
        Add Bluesky handle to a confirmed mail address
        """
        self.login()
        confirmed = self.create_confirmed_email()
        confirmed.set_bluesky_handle(self.bsky_test_account)

        self.assertEqual(
            confirmed.bluesky_handle,
            self.bsky_test_account,
            "Setting Bluesky handle doesn't work?",
        )

    def test_bluesky_handle_for_openid_via_model_handle_does_not_exist(self):
        """
        Add Bluesky handle to a confirmed openid address
        """
        self.login()
        confirmed = self.create_confirmed_openid()
        confirmed.set_bluesky_handle(self.bsky_test_account)

        with contextlib.suppress(Exception):
            confirmed.set_bluesky_handle(f"{self.bsky_test_account}1")
        self.assertNotEqual(
            confirmed.bluesky_handle,
            f"{self.bsky_test_account}1",
            "Setting Bluesky handle that doesn't exist works?",
        )

    def test_bluesky_handle_for_openid_via_model_handle_exists(self):
        """
        Add Bluesky handle to a confirmed openid address
        """
        self.login()
        confirmed = self.create_confirmed_openid()
        confirmed.set_bluesky_handle(self.bsky_test_account)

        self.assertEqual(
            confirmed.bluesky_handle,
            self.bsky_test_account,
            "Setting Bluesky handle doesn't work?",
        )

    def test_bluesky_fetch_mail(self):
        """
        Check if we can successfully fetch a Bluesky avatar via email
        """
        self.login()
        confirmed = self.create_confirmed_email()
        confirmed.set_bluesky_handle(self.bsky_test_account)
        lu = libravatar_url(confirmed.email, https=True)
        lu = lu.replace("https://seccdn.libravatar.org/", reverse("home"))

        response = self.client.get(lu)
        # This is supposed to redirect to the Bluesky proxy
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/blueskyproxy/{confirmed.digest}")

    def test_bluesky_fetch_openid(self):
        """
        Check if we can successfully fetch a Bluesky avatar via OpenID
        """
        self.login()
        confirmed = self.create_confirmed_openid()
        confirmed.set_bluesky_handle(self.bsky_test_account)
        lu = libravatar_url(openid=confirmed.openid, https=True)
        lu = lu.replace("https://seccdn.libravatar.org/", reverse("home"))

        response = self.client.get(lu)
        # This is supposed to redirect to the Bluesky proxy
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/blueskyproxy/{confirmed.digest}")

    def test_assign_bluesky_handle_to_openid(self):
        """
        Assign a Bluesky handle to an OpenID
        """
        self.login()
        confirmed = self.create_confirmed_openid()
        url = reverse("assign_bluesky_handle_to_openid", args=[confirmed.id])
        response = self.client.post(
            url,
            {
                "bluesky_handle": self.bsky_test_account,
            },
            follow=True,
        )
        self.assertEqual(
            response.status_code, 200, "Adding Bluesky handle to OpenID fails?"
        )
        # Fetch object again, as it has changed because of the request
        confirmed.refresh_from_db(fields=["bluesky_handle"])
        self.assertEqual(
            confirmed.bluesky_handle,
            self.bsky_test_account,
            "Setting Bluesky handle doesn't work?",
        )

    def test_assign_bluesky_handle_to_email(self):
        """
        Assign a Bluesky handle to an email

        """
        self.login()
        confirmed = self.create_confirmed_email()
        url = reverse("assign_bluesky_handle_to_email", args=[confirmed.id])
        response = self.client.post(
            url,
            {
                "bluesky_handle": self.bsky_test_account,
            },
            follow=True,
        )
        self.assertEqual(
            response.status_code, 200, "Adding Bluesky handle to Email fails?"
        )
        # Fetch object again, as it has changed because of the request
        confirmed.refresh_from_db(fields=["bluesky_handle"])
        self.assertEqual(
            confirmed.bluesky_handle,
            self.bsky_test_account,
            "Setting Bluesky handle doesn't work?",
        )

    def test_assign_photo_to_mail_removes_bluesky_handle(self):
        """
        Assign a Photo to a mail, removes Bluesky handle
        """
        self.login()
        confirmed = self.create_confirmed_email()
        confirmed.bluesky_handle = self.bsky_test_account
        confirmed.save()

        url = reverse("assign_photo_email", args=[confirmed.id])
        response = self.client.post(
            url,
            {
                "photoNone": True,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200, "Unassigning Photo doesn't work?")
        # Fetch object again, as it has changed because of the request
        confirmed.refresh_from_db(fields=["bluesky_handle"])
        self.assertEqual(
            confirmed.bluesky_handle,
            None,
            "Removing Bluesky handle doesn't work?",
        )

    def test_assign_photo_to_openid_removes_bluesky_handle(self):
        """
        Assign a Photo to a OpenID, removes Bluesky handle
        """
        self.login()
        confirmed = self.create_confirmed_openid()
        confirmed.bluesky_handle = self.bsky_test_account
        confirmed.save()

        url = reverse("assign_photo_openid", args=[confirmed.id])
        response = self.client.post(
            url,
            {
                "photoNone": True,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200, "Unassigning Photo doesn't work?")
        # Fetch object again, as it has changed because of the request
        confirmed.refresh_from_db(fields=["bluesky_handle"])
        self.assertEqual(
            confirmed.bluesky_handle,
            None,
            "Removing Bluesky handle doesn't work?",
        )
