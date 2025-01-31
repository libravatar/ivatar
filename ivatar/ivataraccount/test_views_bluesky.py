# -*- coding: utf-8 -*-
"""
Test our views in ivatar.ivataraccount.views and ivatar.views
"""
# pylint: disable=too-many-lines
import os
import django
from django.test import TestCase
from django.test import Client

# from django.urls import reverse
from django.contrib.auth.models import User

# from django.contrib.auth import authenticate

os.environ["DJANGO_SETTINGS_MODULE"] = "ivatar.settings"
django.setup()

# pylint: disable=wrong-import-position
from ivatar import settings
from ivatar.ivataraccount.models import ConfirmedOpenId, ConfirmedEmail
from ivatar.utils import random_string


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
        confirmed = ConfirmedOpenId.objects.create(
            user=self.user,
            ip_address="127.0.0.1",
            openid=self.openid,
        )

        return confirmed

    def create_confirmed_email(self):
        """
        Create a confirmed email
        """
        confirmed = ConfirmedEmail.objects.create(
            email=self.email,
            user=self.user,
        )

        return confirmed

    # The following tests need to be moved over to the model tests
    # and real web UI tests added
    def test_bluesky_handle_for_mail_via_model_handle_doesnt_exist(self):
        """
        Add Bluesky handle to a confirmed mail address
        """
        self.login()
        confirmed = self.create_confirmed_email()
        confirmed.set_bluesky_handle(self.bsky_test_account)

        try:
            confirmed.set_bluesky_handle(self.bsky_test_account + "1")
        except Exception:
            pass
        self.assertNotEqual(
            confirmed.bluesky_handle,
            self.bsky_test_account + "1",
            "Setting Bluesky handle that doesn exist works?",
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

    def test_bluesky_handle_for_openid_via_model_handle_doesnt_exist(self):
        """
        Add Bluesky handle to a confirmed openid address
        """
        self.login()
        confirmed = self.create_confirmed_openid()
        confirmed.set_bluesky_handle(self.bsky_test_account)

        try:
            confirmed.set_bluesky_handle(self.bsky_test_account + "1")
        except Exception:
            pass
        self.assertNotEqual(
            confirmed.bluesky_handle,
            self.bsky_test_account + "1",
            "Setting Bluesky handle that doesn exist works?",
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
