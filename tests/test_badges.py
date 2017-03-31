import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_github import GitHub
from flask_login import LoginManager

from Hook.models import model_maker
from Hook.ext import HookUI
from Hook.exceptions import RightsException

from unittest import TestCase
from tests.make_moke import make_moke


class TestGithubCommunication(TestCase):
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

        # Models

        # Mokes
        self.hook = HookUI(database=self.db, github=GitHub(app=app), login=LoginManager(app=app), app=app)
        self.Models = self.hook.Models
        self.db.create_all()
        self.Mokes = make_new_latinLit_test = make_moke(self.db, self.Models)
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

    def test_cts_badge_branch(self):
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/cts.svg?branch=issue-45")
        self.assertIn(
            "636/637",
            response.data.decode(),
            "Text should be well shown"
        )

    def test_cts_badge(self):
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/cts.svg")
        self.assertIn(
            "630/637",
            response.data.decode(),
            "Text should be well shown"
        )

        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/cts.svg")
        self.assertIn("636/637", response.data.decode(), "Text should be well shown")

    def test_coverage_branch_badge(self):
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=master")
        self.assertIn("99.79", response.data.decode(), "Master should work correctly")
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=issue-45")
        self.assertIn("99.85", response.data.decode(), "Branch should correctly filter")
        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=master")
        self.assertIn("99.85", response.data.decode(), "Master should work correctly")

    def test_coverage_badge(self):
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg")
        self.assertIn("99.79", response.data.decode(), "Last Master Should Display Correctly")

        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg")
        self.assertIn("99.85", response.data.decode(), "Last Master Should Update Correctly")

