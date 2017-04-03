import os
import requests
from urllib import parse
from logging import getLogger

from flask import Flask, redirect, request, Response, session, g
from flask_sqlalchemy import SQLAlchemy
import flask_github
from flask_login import LoginManager

from Hook.ext import HookUI

from tests.make_moke import make_moke
from tests.baseTest import BaseTest

from unittest import TestCase


class TestGithubCommunication(BaseTest):
    def setUp(self):
        try:
            os.remove("Hook/test.db")
        except:
            """ Something !"""
        super(TestGithubCommunication, self).setUp()
        app = Flask("Hook")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['GITHUB_CLIENT_ID'] = "github_client_id"
        app.config['GITHUB_CLIENT_SECRET'] = "github_client_secret"
        app.config["SECRET_KEY"] = 'super secret key'
        self.db = SQLAlchemy(app)

        # Mokes
        self.hook = HookUI(database=self.db, github=flask_github.GitHub(app=app), login=LoginManager(app=app), app=app)
        self.Models = self.hook.Models
        self.db.create_all()
        self.Mokes = make_moke(self.db, self.Models)

        logger = getLogger(__name__)
        self.called_auth = []
        self.called_auth = []

        @app.route("/authorize")
        def handle_auth():
            logger.info("in /oauth/authorize")
            self.called_auth.append(1)
            self.assertEqual(request.args['client_id'], app.config["GITHUB_CLIENT_ID"])
            logger.debug("client_id OK")
            self.assertEqual(request.args['redirect_uri'], 'http://localhost/callback')
            logger.debug("redirect_uri OK")
            return redirect(request.args['redirect_uri'] + '?code=KODE')

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

    def test_login_reroute(self):
        """ Let's ensure we can login
        """
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 302, "Login should redirect to GitHub Authorize")

        route = parse.urlparse(response.headers["Location"])
        self.assertEqual(route.scheme+"://"+route.netloc+route.path, "https://github.com/login/oauth/authorize",
                         "Login should redirect to GitHub Authorize")
        params = parse.parse_qs(route.query)
        self.assertEqual(
            params,
            {
                "scope": ["user:email,repo:status,admin:repo_hook,read:org"],
                "client_id": ["github_client_id"]
            }
        )

    def test_login_first_time(self):
        """ Ensure first login response from github oauth is gonna create a user """
        index = self.client.get("/").data.decode()
        self.assertIn("Sign-in", index, "We are not logged in")
        with self.logged_in():
            index = self.client.get("/").data.decode()
            self.assertNotIn("Sign-in", index, "We are logged in")
            self.assertIn("Hi octocat!", index, "We are logged in")

        users = self.Models.User.query.all()
        self.assertEqual(len(users), 3, "There should be balmas, ponteineptique and octocat")

    def test_login_nth_time(self):
        """ Ensure first login response from github oauth is gonna create a user """
        index = self.client.get("/").data.decode()
        self.assertIn("Sign-in", index, "We are not logged in")
        with self.logged_in():
            index = self.client.get("/").data.decode()
            self.assertNotIn("Sign-in", index, "We are logged in")
            self.assertIn("Hi octocat!", index, "We are logged in")

        users = self.Models.User.query.all()
        self.assertEqual(len(users), 3, "There should be balmas, ponteineptique and octocat")
        self.client.get("/logout")

        with self.logged_in():
            index = self.client.get("/").data.decode()
            self.assertNotIn("Sign-in", index, "We are logged in")
            self.assertIn("Hi octocat!", index, "We are logged in")

        users = self.Models.User.query.all()
        self.assertEqual(len(users), 3, "There should be balmas, ponteineptique and octocat")


    def test_logout(self):
        with self.client as a:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'user_id'
            self.assertIsInstance(a.get('/logout'), Response)
            self.assertNotIn('oauth_access_token', session)
            self.assertNotIn('user_id', session)
            self.assertNotIn("user", g.__dict__)
