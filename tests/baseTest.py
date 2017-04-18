__author__ = "mozilla"
""" Originally from https://github.com/mozilla/servicebook/blob/master/servicebook/tests/support.py
"""

import os
import requests_mock
import re

from unittest import TestCase
from contextlib import contextmanager
from logging import getLogger

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_github import GitHub
from flask_login import LoginManager

from Hook.ext import HookUI

from tests.make_moke import make_moke
from tests.github_fixtures import make_fixture


class BaseTest(TestCase):
    login = "qwerty"
    name = "Qwerty Uiop"

    def setUp(self):
        try:
            os.remove("Hook/test.db")
        except:
            """ Something !"""
        app = Flask("Hook")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['GITHUB_CLIENT_ID'] = "github_client_id"
        app.config['GITHUB_CLIENT_SECRET'] = "github_client_secret"
        app.config["SECRET_KEY"] = 'super secret key'
        self.db = SQLAlchemy(app)

        # Mokes
        self.hook = HookUI(
            database=self.db, github=GitHub(app=app), login=LoginManager(app=app), app=app,
            commenter_github_access_token="commenter_api"
        )
        self.Models = self.hook.Models
        self.db.create_all()
        self.Mokes = make_moke(self.db, self.Models)

        logger = getLogger(__name__)
        self.called_auth = []
        self.called_auth = []
        self.fixtures = make_fixture(self.Mokes.ponteineptique.github_access_token)

        self.app = app
        self.app.debug = True
        self.client = app.test_client()

    def tearDown(self):
        self.db.session.close()
        self.db.drop_all()
        try:
            os.remove("Hook/test.db")
        except:
            """ Something !"""

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

        github_user = {
            "login": "octocat",
            "id": 1,
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "gravatar_id": "",
            "url": "https://api.github.com/users/octocat",
            "email": "octocat@github.com"
        }
        if access_token in ["nbiousndegoijubdognlksdngndsgmngds"]:
            github_user = {
                "login": "ponteineptique",
                "id": "GitSuperID",
                "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                "gravatar_id": "",
                "url": "https://api.github.com/users/ponteineptique",
                "email": "ponteineptique"
            }
        headers = {'Content-Type': 'application/json'}

        with requests_mock.Mocker() as m:
            m.post(github_matcher, text=github_resp)
            m.get(github_usermatcher, json=github_user, headers=headers)
            self.client.get('/api/github/callback?code=%s' % code)
            self.register_mocks(mocker=m, extra_mocks=extra_mocks)


            # at this point we are logged in
            try:
                yield
            finally:
                # logging out
                self.client.get('/logout')

    @contextmanager
    def mocks(self, extra_mocks=None):
        if extra_mocks is None:
            extra_mocks = []

        with requests_mock.Mocker() as m:
            self.register_mocks(m, extra_mocks)
            # at this point we are logged in
            try:
                yield
            finally:
                # logging out
                pass

    def register_mocks(self, mocker, extra_mocks):
        for verb, url, kwargs in extra_mocks:
            if "json" in kwargs:
                if "headers" in kwargs:
                    kwargs["headers"].update({'Content-Type': "application/json"})
                else:
                    kwargs["headers"] = {'Content-Type': "application/json"}
#                kwargs["json"] = json.dumps(kwargs["json"])
            mocker.register_uri(verb, re.compile(url), **kwargs)
            self.__mocks__ = mocker