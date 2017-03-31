import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_github import GitHub
from flask_login import LoginManager

from Hook.models import model_maker
from Hook.ext import HookUI
from Hook.exceptions import RightsException

from unittest import TestCase


class TestGithubCommunication(TestCase):
    def setUp(self):
        app = Flask("Hook")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.db = SQLAlchemy(app)

        # Models
        self.User, self.Repository, self.RepoTest, self.RepoOwnership, self.UnitTest, self.WordCount = model_maker(self.db)
        self.db.create_all()
        self.hook = HookUI(database=self.db, github=GitHub(app=app), login=LoginManager(app=app))
        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        self.db.session.close()
        self.db.drop_all()
        try:
            os.remove("Hook/test.db")
        except:
            """ Something !"""


