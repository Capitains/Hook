from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from unittest import TestCase
from Hook.models import model_maker
import os


class TestModels(TestCase):
    def setUp(self):
        app = Flask("Hook")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
        self.db = SQLAlchemy(app)

        # Models
        self.User, self.Repository, self.RepoTest, self.RepoOwnership = model_maker(self.db)
        self.db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        self.db.drop_all()

    def createPonteineptique(self):
        ponteineptique = self.User(
            login="ponteineptique",
            email="leponteineptique@gyahoomail.com",
            git_id="GitSuperID",
            github_access_token="nbiousndegoijubdognlksdngndsgmngds"
        )
        self.db.session.add(ponteineptique)
        return ponteineptique

    def createBalmas(self):
        balmas = self.User(
            login="balmas",
            email="balmas@gyahoomail.com",
            git_id="GitSuperIDff",
            github_access_token="nbiousndegoijubdognlksdngndsgmngdsasdfasf"
        )
        self.db.session.add(balmas)
        return balmas

    def commit(self):
        self.db.session.commit()

    def createLatinLit(self):
        latinLit = self.Repository(
            owner="PerseusDl",
            name="canonical-latinLit",
            active=False
        )
        self.db.session.add(latinLit)
        return latinLit

    def test_repo_relationships(self):
        """ Ensure we are able to retrieve, add and delete repositories """
        pi, ll = self.createPonteineptique(), self.createLatinLit()

        # Check we can add old repository easily
        pi.repositories.append(ll)
        self.commit()
        self.assertEqual(ll.users, [pi], "LatinLit should have access to related user")

        # Check we can add new repository easily
        greekLit = self.Repository.find_or_create("PerseusDl", "canonical-greekLit")
        pi.repositories.append(greekLit)
        self.commit()
        self.assertEqual(greekLit.users, [pi], "GreekLit should have access to related user")

        # Check Users have knowledge of these changes
        self.assertCountEqual(pi.repositories, [ll, greekLit], "User should have both repositories")

        # Check that it is possible to do it from the repository perspective
        balmas = self.createBalmas()
        greekLit.users.append(balmas)
        self.commit()
        self.assertEqual(balmas.repositories, [greekLit], "Adding users to repository should be effective easily")
