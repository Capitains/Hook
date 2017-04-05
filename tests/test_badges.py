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


class TestBadgesRoutes(TestCase):
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
        self.hook = HookUI(database=self.db, github=GitHub(app=app), login=LoginManager(app=app), app=app)
        self.Models = self.hook.Models
        self.db.create_all()
        self.Mokes = make_moke(self.db, self.Models)
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

    def test_metadata_count_badge_branch(self):
        """ Ensure route for metadata count badge is working as expected when query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/metadata.svg?branch=issue-45")
        self.assertIn(
            "718/720",
            response.data.decode(),
            "Text should be well shown"
        )

    def test_metadata_count_badge(self):
        """ Ensure route for metadata count badge is working as expected when query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/metadata.svg")
        self.assertIn(
            "719/720",
            response.data.decode(),
            "Text should be well shown"
        )

        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/metadata.svg")
        self.assertIn("718/720", response.data.decode(), "Text should be well shown")

    def test_texts_count_badge_branch(self):
        """ Ensure route for texts count badge is working as expected when query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/texts.svg?branch=issue-45")
        self.assertIn(
            "636/637",
            response.data.decode(),
            "Text should be well shown"
        )

    def test_texts_count_badge(self):
        """ Ensure route for texts count badge is working as expected when no query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/texts.svg")
        self.assertIn(
            "630/637",
            response.data.decode(),
            "Text should be well shown"
        )

        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/texts.svg")
        self.assertIn("636/637", response.data.decode(), "Text should be well shown")

    def test_coverage_branch_badge(self):
        """ Ensure route for coverage badge is working as expected when query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=master")
        self.assertIn("99.79", response.data.decode(), "Master should work correctly")
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=issue-45")
        self.assertIn("99.85", response.data.decode(), "Branch should correctly filter")
        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=master")
        self.assertIn("99.85", response.data.decode(), "Master should work correctly")
        self.assertIn("#97CA00", response.data.decode(), "Color should be green because of success")
        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session, coverage=80.5)
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=master")
        self.assertIn("80.5", response.data.decode(), "Score should be correctly displayed")
        self.assertIn("#dfb317", response.data.decode(), "Color should be orange because not completely failure")
        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session, coverage=25.5)
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg?branch=master")
        self.assertIn("25.5", response.data.decode(), "Score should be correctly displayed")
        self.assertIn("#e05d44", response.data.decode(), "Color should be red because of failure")

    def test_coverage_badge(self):
        """ Ensure route for coverage badge is working as expected when no query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg")
        self.assertIn("99.79", response.data.decode(), "Last Master Should Display Correctly")

        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/coverage.svg")
        self.assertIn("99.85", response.data.decode(), "Last Master Should Update Correctly")

    def test_words_badge(self):
        """ Ensure route for coverage badge is working as expected when no query """
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg")
        response = response.data.decode()
        self.assertIn("1081", response, "Last Master Should have 1081 words")
        self.assertIn("Words", response, "Badge should not be filtered")

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?lang=eng")
        response = response.data.decode()
        self.assertIn("125", response, "Last Master Should have 125 words")
        self.assertIn("eng", response, "Badge should be English only")

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?lang=lat")
        response = response.data.decode()
        self.assertIn("956", response, "Last Master Should have 956 words")
        self.assertIn("lat", response, "Badge should be Latin only")

        with self.app.app_context():
            self.Mokes.make_new_latinLit_test(self.db.session)

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg")
        response = response.data.decode()
        self.assertIn("2263", response, "Last Master Should have 2263 words")
        self.assertIn("Words", response, "Badge should not be filtered")

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?lang=eng")
        response = response.data.decode()
        self.assertIn("125", response, "Last Master Should have 125 words")
        self.assertIn("eng", response, "Badge should be English only")

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?lang=lat")
        response = response.data.decode()
        self.assertIn("1050", response, "Last Master Should have 956 words")
        self.assertIn("lat", response, "Badge should be Latin only")

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?lang=ger")
        response = response.data.decode()
        self.assertIn("1088", response, "Last Master Should have 956 words")
        self.assertIn("ger", response, "Badge should be Latin only")

    def test_wrong_words_badges(self):
        """ Ensure route for badges are failing with wrong badges"""
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-farsiLit/words.svg")
        self.assertEqual(response.status_code, 404, "Error should result in 404")
        self.assertIn("Unknown repository", response.data.decode())

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?lang=fre")
        self.assertEqual(response.status_code, 404, "Error should result in 404")
        self.assertIn("Unknown language", response.data.decode())

        with self.client.application.app_context():
            test = self.Models.RepoTest.query.get(2)
            for word in test.words_count:
                test.words_count.remove(word)
            self.db.session.commit()

        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-latinLit/words.svg?uuid=2")
        self.assertEqual(response.status_code, 404, "Error should result in 404")
        self.assertIn("Unknown repository's test", response.data.decode())

    def test_wrong_badges(self):
        """ Ensure route for badges are failing with wrong badges"""
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-farsiLit/coverage.svg")
        self.assertEqual(response.status_code, 404, "Error should result in 404")
        self.assertIn("Unknown repository", response.data.decode())
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-farsiLit/metadata.svg")
        self.assertEqual(response.status_code, 404, "Error should result in 404")
        self.assertIn("Unknown repository", response.data.decode())
        response = self.client.get("/api/hook/v2.0/badges/PerseusDl/canonical-farsiLit/texts.svg")
        self.assertEqual(response.status_code, 404, "Error should result in 404")
        self.assertIn("Unknown repository", response.data.decode())
