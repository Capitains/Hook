from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from unittest import TestCase
from Hook.models import model_maker
from Hook.exceptions import RightsException
import os
from time import sleep


class TestModels(TestCase):
    def setUp(self):
        app = Flask("Hook")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.db = SQLAlchemy(app)

        # Models
        self.User, self.Repository, self.RepoTest, self.RepoOwnership, self.UnitTest, self.WordCount = model_maker(self.db)
        self.db.create_all()
        self.client = app.test_client()
        self.former_unit = {
            "data/stoa0033a/__cts__.xml": True,
            "data/stoa0033a/tlg028/__cts__.xml": True,
            "data/stoa0033a/tlg028/stoa0033a.tlg028.1st1K-grc1.xml": True,
            "data/stoa0033a/tlg043/__cts__.xml": True,
            "data/stoa0033a/tlg043/stoa0033a.tlg043.1st1K-grc1.xml": True,
            "data/stoa0121/__cts__.xml": False,
            "data/stoa0121/stoa001/__cts__.xml": False,
            "data/stoa0121/stoa001/stoa0121.stoa001.opp-grc1.xml": False,
            "data/tlg0015/__cts__.xml": True,
            "data/tlg0015/tlg001/__cts__.xml": True,
            "data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml": False,
            "data/tlg0018/__cts__.xml": True,
            "data/tlg0018/tlg001/__cts__.xml": True,
            "data/tlg0018/tlg001/tlg0018.tlg001.opp-grc1.xml": False,
        }

    def tearDown(self):
        self.db.session.close()
        self.db.drop_all()
        try:
            os.remove("Hook/test.db")
        except:
            """ Something !"""

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

    def createGreekLit(self):
        greekLit = self.Repository(
            owner="PerseusDl",
            name="canonical-greekLit",
            active=False
        )
        self.db.session.add(greekLit)
        return greekLit

    def makeTest(self, repo):
        test = self.RepoTest(
            branch="master",
            repository=repo.uuid,
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544",
            travis_build_id="25",
            travis_user="sonofmun",
            travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637,
            texts_passing=630,
            metadata_total=718,
            metadata_passing=713,
            coverage=99.79,
            nodes_count=113109
        )
        self.db.session.add(test)
        self.commit()
        return test

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

    def test_switch_repo(self):
        """ Check that switch works correctly """
        pi, ll, gl, ba = self.createPonteineptique(), self.createLatinLit(), self.createGreekLit(), self.createBalmas()
        pi.repositories = [ll, gl]
        ba.repositories = [gl]
        self.commit()

        self.assertEqual(ll.active, False, "Repositories are inactive by default")
        self.assertEqual(ll.switch_active(pi), True, "Repositories are switched correctly")
        self.assertEqual(gl.active, False, "Repositories are inactive by default")
        self.assertEqual(gl.switch_active(ba), True, "Repositories are switched correctly")
        with self.assertRaisesRegex(RightsException, "balmas has no rights to write over PerseusDl/canonical-latinLit"):
            ll.switch_active(ba)

    def test_active_repo(self):
        """ Check that switch works correctly """
        pi, ll, gl, ba = self.createPonteineptique(), self.createLatinLit(), self.createGreekLit(), self.createBalmas()
        pi.repositories = [ll, gl]
        ba.repositories = [gl]
        self.commit()

        # Tests with all active
        ll.active, gl.active = True, True
        self.commit()
        self.assertCountEqual(pi.active_repositories, [ll, gl], "Only active repositories should be shown")
        self.assertCountEqual(ba.active_repositories, [gl], "Only active repositories should be shown")

        # Tests with partial active
        ll.active = False
        self.commit()
        self.assertEqual(pi.active_repositories, [gl], "Only active repositories should be shown")
        self.assertEqual(ba.active_repositories, [gl], "Only active repositories should be shown")

    def test_user_organization(self):
        pi, ll, gl, ba = self.createPonteineptique(), self.createLatinLit(), self.createGreekLit(), self.createBalmas()
        pi.repositories = [ll, gl]
        ba.repositories = [gl]
        self.commit()

        self.assertCountEqual(pi.organizations, ["PerseusDl"], "Organization should be displayed")
        self.assertEqual(ba.organizations, ["PerseusDl"], "Organizations should be displayed")

        # User's name should be filtered out
        pi.repositories.append(self.Repository.find_or_create("ponteineptique", "something", False))
        ba.repositories.append(self.Repository.find_or_create("ponteineptique", "something", False))
        self.commit()

        self.assertCountEqual(
            pi.organizations, ["PerseusDl"],
            "Organization should be displayed and have user own name filtered"
        )
        self.assertCountEqual(ba.organizations, ["PerseusDl", "ponteineptique"], "Organizations should be displayed")

    def test_repo_tests(self):
        """ Ensure that tests are correctly connected """
        pi, ll, gl, ba = self.createPonteineptique(), self.createLatinLit(), self.createGreekLit(), self.createBalmas()
        self.commit()
        test = self.makeTest(gl)

        gl.tests.append(test)
        self.commit()
        self.assertEqual(gl.last_master_test, test, "Last master test should be resolved correctly")

        sleep(0.1)

        test2 = self.RepoTest(
            branch="master",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544",
            travis_build_id="27",
            travis_user="sonofmun",
            travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637,
            texts_passing=630,
            metadata_total=718,
            metadata_passing=718,
            coverage=99.79,
            nodes_count=113109,
            repository=gl.uuid
        )
        gl.tests.append(test2)
        self.commit()
        self.assertEqual(gl.last_master_test, test2, "Last master test should be resolved correctly")

        sleep(0.1)

        test3 = self.RepoTest(
            branch="different_branch",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544",
            travis_build_id="27",
            travis_user="sonofmun",
            travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637,
            texts_passing=635,
            metadata_total=720,
            metadata_passing=719,
            coverage=99.79,
            nodes_count=113179,
            repository=gl.uuid
        )
        gl.tests.append(test3)
        self.commit()
        self.assertEqual(
            gl.last_master_test, test2,
            "Last master test should be resolved correctly even on name branch"
        )

        sleep(0.1)

        test4 = self.RepoTest(
            branch="master",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544",
            travis_build_id="52",
            travis_user="sonofmun",
            travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637,
            texts_passing=635,
            metadata_total=720,
            metadata_passing=719,
            coverage=99.79,
            nodes_count=113179,
            repository=ll.uuid
        )
        ll.tests.append(test4)
        self.commit()
        self.assertEqual(
            gl.last_master_test, test2,
            "Last master test should be resolved correctly from different repo"
        )

    def test_unit_diffs(self):
        pi, ll = self.createPonteineptique(), self.createLatinLit()
        self.commit()
        test = self.RepoTest(
            branch="master",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544",
            travis_build_id="27",
            travis_user="sonofmun",
            travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637,
            texts_passing=635,
            metadata_total=720,
            metadata_passing=719,
            coverage=99.79,
            nodes_count=113179,
            repository=ll.uuid
        )
        self.db.session.add(test)
        self.commit()
        test.save_units(self.former_unit)

        self.commit()
        stoa15 = [
            test.get_unit("data/tlg0015/__cts__.xml"),
            test.get_unit("data/tlg0015/tlg001/__cts__.xml"),
            test.get_unit("data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml")
        ]
        self.assertEqual(
            stoa15, [True, True, False],
            "Relationship and saving dict should work correctly"
        )
        self.assertEqual(
            test.units_as_dict, self.former_unit,
            "Dictionary of units should be equivalent"
        )

    def test_repo_word_count(self):
        pi, ll = self.createPonteineptique(), self.createLatinLit()
        self.commit()
        test = self.RepoTest(
            branch="master",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544",
            travis_build_id="27",
            travis_user="sonofmun",
            travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637,
            texts_passing=635,
            metadata_total=720,
            metadata_passing=719,
            coverage=99.79,
            nodes_count=113179,
            repository=ll.uuid
        )
        self.db.session.add(test)
        self.commit()
        test.save_word_counts({
            "eng": 55555,
            "lat": 7899984,
            "78945": 78945
        })

        self.commit()
        self.assertEqual(
            test.words_count_as_dict,
            {
                "eng": 55555,
                "lat": 7899984,
                "78945": 78945
            },
            "Relationship and saving dict should work correctly"
        )

    def test_diff(self):
        pi, ll = self.createPonteineptique(), self.createLatinLit()
        self.commit()
        # Create first test
        test = self.RepoTest(
            branch="master",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544", travis_build_id="27",
            travis_user="sonofmun", travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637, texts_passing=635, metadata_total=720, metadata_passing=719, coverage=99.79,
            nodes_count=113179, repository=ll.uuid
        )
        self.db.session.add(test)
        self.commit()
        test.save_word_counts({
            "eng": 55555,
            "lat": 7899984,
            "ger": 78945
        })
        test.save_units(self.former_unit)
        self.commit()
        sleep(0.1)
        # Create second test
        self.former_unit["data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml"] = True
        self.former_unit["data/tlg0015/tlg001/__cts__.xml"] = False
        self.former_unit["data/tlg0015/tlg002/__cts__.xml"] = False
        del self.former_unit["data/tlg0015/__cts__.xml"]
        second_repo = self.RepoTest(
            branch="n1",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544", travis_build_id="27",
            travis_user="sonofmun", travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637, texts_passing=636, metadata_total=725, metadata_passing=719, coverage=99.78,
            nodes_count=113135, repository=ll.uuid
        )
        self.db.session.add(second_repo)
        self.db.session.commit()
        diff = second_repo.diff(
            test, self.former_unit, {
                "eng": 55556,
                "lat": 7899973,
                "ger": 78945
            }
        )
        self.assertCountEqual(diff,
                         {'Global': [('Changed', 'texts_passing', '+1'), ('Changed', 'coverage', '-0.01'),
                                     ('Changed', 'nodes_count', '-44'), ('Changed', 'metadata_total', '+5')],
                          'Units': [('Changed', 'data/tlg0015/tlg001/__cts__.xml', 'Passing'),
                                    ('Deleted', 'data/tlg0015/__cts__.xml', ''),
                                    ('Changed', 'data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml', 'Passing'),
                                    ('New', 'data/tlg0015/tlg002/__cts__.xml', '')],
                          'Words': [('Changed', 'lat', '-11'), ('Changed', 'eng', '+1')]},
                         "Diff should be well computed"
                         )
        sleep(0.1)

        # Create third test
        third_repo = self.RepoTest(
            branch="n2",
            travis_uri="https://travis-ci.org/sonofmun/First1KGreek/builds/216262544", travis_build_id="287",
            travis_user="sonofmun", travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
            texts_total=637, texts_passing=636, metadata_total=725, metadata_passing=719, coverage=99.79,
            nodes_count=113135, repository=ll.uuid
        )
        self.db.session.add(third_repo)
        self.db.session.commit()
        diff = third_repo.diff(
            test, self.former_unit, {
                "eng": 55556,
                "lat": 7899990,
                "ger": 78945
            }
        )
        print(diff)
        self.assertEqual(diff,
                         {'Global': [('Changed', 'texts_passing', '+1'),
                                     ('Changed', 'nodes_count', '-44'), ('Changed', 'metadata_total', '+5')],
                          'Units': [('Changed', 'data/tlg0015/tlg001/__cts__.xml', 'Passing'),
                                    ('Deleted', 'data/tlg0015/__cts__.xml', ''),
                                    ('Changed', 'data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml', 'Passing'),
                                    ('New', 'data/tlg0015/tlg002/__cts__.xml', '')],
                          'Words': [('Changed', 'lat', '+3'), ('Changed', 'eng', '+1')]},
                         "Diff should be well computed"
                         )
