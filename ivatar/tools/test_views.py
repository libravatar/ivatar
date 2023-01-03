# -*- coding: utf-8 -*-
"""
Test our views in ivatar.ivataraccount.views and ivatar.views
"""
# pylint: disable=too-many-lines
import os
import django
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

os.environ["DJANGO_SETTINGS_MODULE"] = "ivatar.settings"
django.setup()

# pylint: disable=wrong-import-position
from ivatar.utils import random_string

# pylint: enable=wrong-import-position


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

    def test_check_mail(self):
        """
        Test check page
        """
        self.login()
        response = self.client.get(reverse("tools_check"))
        self.assertEqual(response.status_code, 200, "no 200 ok?")
        response = self.client.post(
            reverse("tools_check"),
            data={"mail": "test@test.com", "size": "85"},
            follow=True,
        )

        self.assertContains(
            response,
            'value="test@test.com"',
            1,
            200,
            "Value not set again!?",
        )

        self.assertContains(
            response,
            "b642b4217b34b1e8d3bd915fc65c4452",
            3,
            200,
            "Wrong md5 hash!?",
        )
        self.assertContains(
            response,
            "f660ab912ec121d1b1e928a0bb4bc61b15f5ad44d5efdc4e1c92a25e99b8e44a",
            3,
            200,
            "Wrong sha256 hash!?",
        )
        self.assertContains(
            response,
            'value="85"',
            1,
            200,
            "Size should be set based on post params!?",
        )

    def test_check_openid(self):
        """
        Test check page
        """
        self.login()
        response = self.client.get(reverse("tools_check"))
        self.assertEqual(response.status_code, 200, "no 200 ok?")
        response = self.client.post(
            reverse("tools_check"),
            data={"openid": "https://test.com", "size": "85"},
            follow=True,
        )

        self.assertContains(
            response,
            'value="https://test.com"',
            1,
            200,
            "Value not set again!?",
        )

        self.assertContains(
            response,
            "396936bd0bf0603d6784b65d03e96dae90566c36b62661f28d4116c516524bcc",
            3,
            200,
            "Wrong sha256 hash!?",
        )
        self.assertContains(
            response,
            'value="85"',
            1,
            200,
            "Size should be set based on post params!?",
        )

    def test_check_domain(self):
        """
        Test check domain page
        """
        self.login()
        response = self.client.get(reverse("tools_check_domain"))
        self.assertEqual(response.status_code, 200, "no 200 ok?")
        response = self.client.post(
            reverse("tools_check_domain"),
            data={"domain": "linux-kernel.at"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200, "no 200 ok?")
        self.assertContains(
            response,
            "http://avatars.linux-kernel.at",
            2,
            200,
            "Not responing with right URL!?",
        )
        self.assertContains(
            response,
            "https://avatars.linux-kernel.at",
            2,
            200,
            "Not responing with right URL!?",
        )
