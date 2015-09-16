from flask.ext.testing import TestCase
from flask import Flask
import Hook.models

import Hook.models.user

class TestUser(TestCase):
    """ Test User classes """

    def create_app(self):

        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    def test_required(self):
        """ Test required property """
        keys = []
        try:
            u = Hook.models.User(mail="something")
            u.save()
        except Exception as E:
            keys += list(E.errors.keys())

        keys.sort()
        self.assertEqual(keys, [
            "git_id",
            "github_access_token",
            "login",
            "uuid"
        ])

    def test_working(self):
        u = Hook.models.User(
            mail="something",
            git_id=567,
            github_access_token="123456",
            uuid="adfff",
            login="username"
        )
        u.save()