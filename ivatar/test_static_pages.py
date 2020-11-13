'''
Test our views in ivatar.ivataraccount.views and ivatar.views
'''
# pylint: disable=too-many-lines
import os
import django
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

from ivatar.utils import random_string

os.environ['DJANGO_SETTINGS_MODULE'] = 'ivatar.settings'
django.setup()


class Tester(TestCase):  # pylint: disable=too-many-public-methods
    '''
    Main test class
    '''
    client = Client()
    user = None
    username = random_string()
    password = random_string()
    email = '%s@%s.%s' % (username, random_string(), random_string(2))
    # Dunno why random tld doesn't work, but I'm too lazy now to investigate
    openid = 'http://%s.%s.%s/' % (username, random_string(), 'org')

    def login(self):
        '''
        Login as user
        '''
        self.client.login(username=self.username, password=self.password)

    def setUp(self):
        '''
        Prepare for tests.
        - Create user
        '''
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )

    def test_contact_page(self):
        """
        Test contact page
        """
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200, 'no 200 ok?')

    def test_description_page(self):
        """
        Test description page
        """
        response = self.client.get(reverse('description'))
        self.assertEqual(response.status_code, 200, 'no 200 ok?')

    def test_security_page(self):
        """
        Test security page
        """
        response = self.client.get(reverse('security'))
        self.assertEqual(response.status_code, 200, 'no 200 ok?')
