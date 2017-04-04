import os
import re
from urllib import parse
from logging import getLogger
from json import loads
from bs4 import BeautifulSoup

from flask import Flask, redirect, request, Response, session, g
from flask_sqlalchemy import SQLAlchemy
import flask_github
from flask_login import LoginManager

from Hook.ext import HookUI

from tests.make_moke import make_moke
from tests.baseTest import BaseTest
from tests.github_fixtures import make_fixture


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
        self.fixtures = make_fixture(self.Mokes.ponteineptique.github_access_token)

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

    def test_fetch_repositories(self):
        """ Test routes to fetch, update or get repositories """
        self.maxDiff = None
        with self.logged_in(
            access_token="nbiousndegoijubdognlksdngndsgmngds",
            extra_mocks=[
                (
                    "get",
                    "https://api.github.com/user/repos",
                    dict(
                        json=self.fixtures['./tests/fixtures/repos_ponteineptique.response.json'][0],
                        headers=self.fixtures['./tests/fixtures/repos_ponteineptique.response.json'][1]
                    )
                 ),
                (
                    "get",
                    re.compile("https://api.github.com/user/repos\?.*page=2"),
                    dict(
                        json=self.fixtures['./tests/fixtures/repos_ponteineptique.page2.response.json'][0],
                        headers=self.fixtures['./tests/fixtures/repos_ponteineptique.page2.response.json'][1]
                    )
                 )
            ]
        ):
            index = self.client.get("/").data.decode()
            self.assertNotIn("Sign-in", index, "We are logged in")
            self.assertIn("Hi ponteineptique!", index, "We are logged in")

            # We check
            repositories = loads(self.client.get("/api/hook/v2.0/user/repositories").data.decode())
            self.assertEqual(repositories, {"repositories": []}, "No repository on first get")

            # We refresh by posting
            repositories = loads(self.client.post("/api/hook/v2.0/user/repositories").data.decode())
            repositories["repositories"] = sorted(repositories["repositories"], key=lambda x: x["name"])
            self.assertEqual(
                repositories,
                {
                    "repositories": [
                        {'name': 'canonical-greekLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-latinLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-norseLit', 'owner': 'PerseusDL'},
                        {'name': 'octodog', 'owner': 'octocat'}
                    ]
                },
                "Github API is parsed correctly"
            )

        with self.logged_in(
            access_token="nbiousndegoijubdognlksdngndsgmngds",
            extra_mocks=[
                (
                    "get",
                    "https://api.github.com/user/repos",
                    dict(
                        json=self.fixtures['./tests/fixtures/repos_ponteineptique.response.json'][0],
                        headers=self.fixtures['./tests/fixtures/repos_ponteineptique.response.json'][1]
                    )
                 ),
                (
                    "get",
                    re.compile("https://api.github.com/user/repos\?.*page=2"),
                    dict(
                        json=self.fixtures['./tests/fixtures/repos_ponteineptique.page2.alt.response.json'][0],
                        headers=self.fixtures['./tests/fixtures/repos_ponteineptique.page2.alt.response.json'][1]
                    )
                 )
            ]
        ):
            # We check it was saved
            repositories = loads(self.client.get("/api/hook/v2.0/user/repositories").data.decode())
            repositories["repositories"] = sorted(repositories["repositories"], key=lambda x: x["name"])
            self.assertEqual(
                repositories,
                {
                    "repositories": [
                        {'name': 'canonical-greekLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-latinLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-norseLit', 'owner': 'PerseusDL'},
                        {'name': 'octodog', 'owner': 'octocat'}
                    ]
                },
                "When logging in back, we should have the same old repos"
            )

            # We update by posting
            repositories = loads(self.client.post("/api/hook/v2.0/user/repositories").data.decode())
            repositories["repositories"] = sorted(repositories["repositories"], key=lambda x: x["name"])
            self.assertEqual(
                repositories,
                {
                    "repositories": [
                        {'name': 'canonical-greekLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-latinLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-norseLit', 'owner': 'PerseusDL'},
                        {'name': 'octodog', 'owner': 'octocat'},
                        {'name': 'oneKGreek', 'owner': 'ponteineptique'}
                    ]
                },
                "Github API is parsed correctly"
            )

            # We check it was saved and cleared before
            repositories = loads(self.client.get("/api/hook/v2.0/user/repositories").data.decode())
            repositories["repositories"] = sorted(repositories["repositories"], key=lambda x: x["name"])
            self.assertEqual(
                repositories,
                {
                    "repositories": [
                        {'name': 'canonical-greekLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-latinLit', 'owner': 'PerseusDL'},
                        {'name': 'canonical-norseLit', 'owner': 'PerseusDL'},
                        {'name': 'octodog', 'owner': 'octocat'},
                        {'name': 'oneKGreek', 'owner': 'ponteineptique'}
                    ]
                },
                "Old repos should have been cleared, new ones should be there !"
            )

    def test_index_repositories(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        with self.logged_in(access_token="nbiousndegoijubdognlksdngndsgmngds"):
            index = self.client.get("/").data.decode()
            self.assertIn('href="/repo/PerseusDl/canonical-greekLit"', index, "GreekLit link should be there")
            self.assertIn('href="/repo/PerseusDl/canonical-greekLit"', index, "LatinLit link should be there")

    def test_activate_repositories(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        with self.logged_in(access_token="nbiousndegoijubdognlksdngndsgmngds"):
            index = self.client.get("/").data.decode()
            self.assertIn('href="/repo/PerseusDl/canonical-greekLit"', index, "GreekLit link should be there")
            self.assertIn('href="/repo/PerseusDl/canonical-greekLit"', index, "LatinLit link should be there")
            index = BeautifulSoup(self.client.get("/").data.decode(), 'html.parser')
            self.assertEqual(
                len(index.select("#repos .repo-menu-card a")), 0,
                "There should be no active repo in menu"
            )

            activate = self.client.put("/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit")
            self.assertEqual(activate.status_code, 200, "Request should be positive")

            index = BeautifulSoup(self.client.get("/").data.decode(), 'html.parser')
            self.assertEqual(
                index.select("#repos .repo-menu-card a")[0]["href"], "/repo/PerseusDl/canonical-greekLit",
                "Active repo should be in menu"
            )

        with self.logged_in(access_token="nbiousndegoijubdognlksdngndsgmngds"):
            " Relogging should be okay "
            index = BeautifulSoup(self.client.get("/").data.decode(), 'html.parser')
            self.assertEqual(
                index.select("#repos .repo-menu-card a")[0]["href"], "/repo/PerseusDl/canonical-greekLit",
                "Active repo should be in menu"
            )

            # We can switch off
            activate = self.client.put("/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit")
            self.assertEqual(activate.status_code, 200, "Request should be positive")

            index = BeautifulSoup(self.client.get("/").data.decode(), 'html.parser')
            self.assertEqual(len(index.select("#repos .repo-menu-card a")), 0, "There should be no active repo in menu")

            # Wrong repo is 404
            activate = self.client.put("/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit-fake")
            self.assertEqual(activate.status_code, 404, "Request should be positive")