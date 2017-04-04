__author__ = "mozilla"
""" Originally from https://github.com/mozilla/servicebook/blob/master/servicebook/tests/support.py
"""

from unittest import TestCase
from contextlib import contextmanager
import json
import re
import os
import requests_mock


github_user = {
    "login": "octocat",
    "id": 1,
    "avatar_url": "https://github.com/images/error/octocat_happy.gif",
    "gravatar_id": "",
    "url": "https://api.github.com/users/octocat",
    "email": "octocat@github.com"
}


class BaseTest(TestCase):
    login = "qwerty"
    name = "Qwerty Uiop"

    @contextmanager
    def logged_in(self, access_token="yup", extra_mocks=None):
        if extra_mocks is None:
            extra_mocks = []

        # let's log in
        self.client.get('/login')
        # redirects to github, let's fake the callback
        code = 'yeah'
        github_resp = 'access_token=%s' % access_token
        github_matcher = re.compile('github.com/')
        github_usermatcher = re.compile('https://api.github.com/user')
        headers = {'Content-Type': 'application/json'}

        with requests_mock.Mocker() as m:
            m.post(github_matcher, text=github_resp)
            m.get(github_usermatcher, json=github_user)
            self.client.get('/api/github/callback?code=%s' % code)
            for verb, url, kwargs in extra_mocks:
                m.register_uri(verb, re.compile(url), **kwargs)

            # at this point we are logged in
            try:
                yield
            finally:
                # logging out
                self.client.get('/logout')