import re
from urllib import parse
from json import loads
from bs4 import BeautifulSoup
import datetime

from flask import Response, session, g
from tests.baseTest import BaseTest


class TestGithubCommunication(BaseTest):
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

    def test_wrong_repo_disconnected(self):
        response = self.client.get("/repo/PerseusDl/canonical-greekolatinLit")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Unknown Repository", response.data.decode())

    def test_single_repo_disconnected(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        self.Mokes.make_new_latinLit_test(coverage=55.0, session=self.db.session)
        response = self.client.get("/repo/PerseusDl/canonical-latinLit").data.decode()

        self.assertNotIn(
            "Settings", response, "There is no Settings for unlogged people"
        )
        self.assertNotIn("$('#state')", response, "We have the switch script")
        index = BeautifulSoup(response, 'html.parser')

        tests = index.select("#body tbody tr")
        self.assertEqual(len(tests), 3, "There should be 3 tests")
        last_test = tests[0]
        self.assertEqual(
            len(last_test.select('a[href="/repo/PerseusDl/canonical-latinLit/3"]')), 1,
            "There should be a link to the last test"
        )
        self.assertEqual(
            len(last_test.select('a[href="https://github.com/PerseusDL/canonical-latinLit/commit/'
                                 '7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments"]')),
            1,
            "There should be a link to the commit on GitHub"
        )
        self.assertIn("<td>55.0</td>", str(last_test), "There should be the coverage shown")
        second_test = tests[1]
        self.assertEqual(
            len(second_test.select('a[href="/repo/PerseusDl/canonical-latinLit/2"]')), 1,
            "There should be a link to the second test"
        )
        self.assertIn("<td>99.85</td>", str(second_test), "There should be the coverage shown")

    def test_single_repo_connected(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        self.Mokes.make_new_latinLit_test(coverage=55.0, session=self.db.session)
        with self.logged_in(access_token="nbiousndegoijubdognlksdngndsgmngds"):
            response = self.client.get("/repo/PerseusDl/canonical-latinLit").data.decode()

            self.assertIn(
                "Settings", response, "There is no Settings for unlogged people"
            )
            self.assertIn("$('#state')", response, "We have the switch script")
            index = BeautifulSoup(response, 'html.parser')

            tests = index.select("#body tbody tr")
            self.assertEqual(len(tests), 3, "There should be 3 tests")
            last_test = tests[0]
            self.assertEqual(
                len(last_test.select('a[href="/repo/PerseusDl/canonical-latinLit/3"]')), 1,
                "There should be a link to the last test"
            )
            self.assertEqual(
                len(last_test.select('a[href="https://github.com/PerseusDL/canonical-latinLit/commit/'
                                     '7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments"]')),
                1,
                "There should be a link to the commit on GitHub"
            )
            self.assertIn("<td>55.0</td>", str(last_test), "There should be the coverage shown")
            second_test = tests[1]
            self.assertEqual(
                len(second_test.select('a[href="/repo/PerseusDl/canonical-latinLit/2"]')), 1,
                "There should be a link to the second test"
            )
            self.assertIn("<td>99.85</td>", str(second_test), "There should be the coverage shown")

    def test_single_repo_lots_of_tests(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        self.Mokes.make_lots_of_tests(
            45, self.db.session, self.Mokes.greekLit,
            coverage_ends_at=75.0, datetime_starts_at=datetime.datetime(2017, 4, 5, 7, 4, 22, tzinfo=None)
        )

        page1 = BeautifulSoup(self.client.get("/repo/PerseusDl/canonical-greekLit").data.decode(), 'html.parser')
        self.assertEqual(
            page1.select('a.next')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=2",
            "There should be a next link"
        )
        self.assertEqual(
            page1.select('a.last')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=3",
            "There should be a last link"
        )
        self.assertEqual(
            len(page1.select('a.prev')), 0,
            "There should not be a prev link"
        )
        self.assertEqual(
            len(page1.select('a.first')), 0,
            "There should not be a firstLink"
        )
        tests = page1.select("#body tbody tr")
        self.assertEqual(len(tests), 20, "There should be 20 tests")

        last_test = tests[0]
        self.assertEqual(
            len(last_test.select('a[href="/repo/PerseusDl/canonical-greekLit/47"]')), 1,
            "There should be a link to the last test"
        )
        self.assertEqual(
            len(last_test.select('a[href="https://github.com/PerseusDL/canonical-latinLit/commit/'
                                 'fb644351560d8296fe6da332236b1f8d61b2828a#all_commit_comments"]')),
            1,
            "There should be a link to the commit on GitHub"
        )
        self.assertIn("<td>75.0</td>", str(last_test), "There should be the coverage shown")

        ###############
        #
        # Second Page
        #
        ###############
        page2 = BeautifulSoup(self.client.get("/repo/PerseusDl/canonical-greekLit?page=2").data.decode(), 'html.parser')
        self.assertEqual(
            page2.select('a.prev')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=1",
            "There should be a Previous link"
        )
        self.assertEqual(
            page2.select('a.first')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=1",
            "There should be a First link"
        )
        self.assertEqual(
            page2.select('a.next')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=3",
            "There should be a Next link"
        )
        self.assertEqual(
            page2.select('a.last')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=3",
            "There should be a last Link"
        )
        tests = page2.select("#body tbody tr")
        self.assertEqual(len(tests), 20, "There should be 20 tests")

        last_test = tests[0]
        self.assertEqual(
            len(last_test.select('a[href="/repo/PerseusDl/canonical-greekLit/27"]')), 1,
            "There should be a link to the last test"
        )
        self.assertEqual(
            len(last_test.select('a[href="https://github.com/PerseusDL/canonical-latinLit/commit/'
                                 'f6e1126cedebf23e1463aee73f9df08783640400#all_commit_comments"]')),
            1,
            "There should be a link to the commit on GitHub"
        )
        self.assertIn("<td>65.0</td>", str(last_test), "There should be the coverage shown")

        ###############
        #
        # Third Page
        #
        ###############
        page3 = BeautifulSoup(self.client.get("/repo/PerseusDl/canonical-greekLit?page=3").data.decode(), 'html.parser')
        self.assertEqual(
            page3.select('a.prev')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=2",
            "There should be a Previous link"
        )
        self.assertEqual(
            page3.select('a.first')[0]["href"], "/repo/PerseusDl/canonical-greekLit?page=1",
            "There should be a First link"
        )
        self.assertEqual(
            len(page3.select('a.next')), 0,
            "There should not be a Next link"
        )
        self.assertEqual(
            len(page3.select('a.last')), 0,
            "There should not be a last Link"
        )
        tests = page3.select("#body tbody tr")
        self.assertEqual(len(tests), 5, "There should be 5 tests")

        last_test = tests[0]
        self.assertEqual(
            len(last_test.select('a[href="/repo/PerseusDl/canonical-greekLit/7"]')), 1,
            "There should be a link to the last test"
        )
        self.assertEqual(
            len(last_test.select('a[href="https://github.com/PerseusDL/canonical-latinLit/commit/'
                                 'ac3478d69a3c81fa62e60f5c3696165a4e5e6ac4#all_commit_comments"]')),
            1,
            "There should be a link to the commit on GitHub"
        )
        self.assertIn("<td>55.0</td>", str(last_test), "There should be the coverage shown")

    def test_single_repotest(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        response = self.client.get("/repo/PerseusDl/canonical-latinLit/2").data.decode()
        index = BeautifulSoup(response, 'html.parser')
        self.assertEqual(index.select('dd[aria-label="Coverage"]')[0].text, "99.85")
        self.assertEqual(index.select('dd[aria-label="Text Count"]')[0].text, "636/637")
        self.assertEqual(index.select('dd[aria-label="Metadata Count"]')[0].text, "718/720")
        self.assertEqual(index.select('dd[aria-label="Citation Nodes"]')[0].text, "113179")
        self.assertEqual(index.select('dd[aria-label="Words in eng"]')[0].text, "125")
        self.assertEqual(index.select('dd[aria-label="Words in lat"]')[0].text, "1050")
        self.assertEqual(index.select('dd[aria-label="Words in ger"]')[0].text, "1088")
        self.assertEqual(index.select('dd[aria-label="Travis Build"] a')[0]["href"],
                         "https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262555")
        self.assertEqual(index.select('dd[aria-label="Github Comment"] a')[0]["href"],
                         "https://github.com/PerseusDL/canonical-latinLit/commit/7d3d6a0b62f0d244b684843"
                         "c7546906d742013fd#all_commit_comments")
        self.assertEqual(
            len(index.select("div.dl-horizontal.card div.left.success")), 1,
            "Success class should be applied"
        )

        self.Mokes.make_new_latinLit_test(session=self.db.session, coverage=75.01)
        response = self.client.get("/repo/PerseusDl/canonical-latinLit/3").data.decode()
        index = BeautifulSoup(response, 'html.parser')
        self.assertEqual(
            len(index.select("div.dl-horizontal.card div.left.acceptable")), 1,
            "Acceptable class should be applied"
        )

        self.Mokes.make_new_latinLit_test(session=self.db.session, coverage=74.99)
        response = self.client.get("/repo/PerseusDl/canonical-latinLit/4").data.decode()
        index = BeautifulSoup(response, 'html.parser')
        self.assertEqual(
            len(index.select("div.dl-horizontal.card div.left.failed")), 1,
            "Failure class should be applied"
        )

    def test_update_repository_token(self):
        """ Test that index links all known repositories """
        self.Mokes.add_repo_to_pi()
        response = self.client.get("/repo/PerseusDl/canonical-latinLit").data.decode()
        index = BeautifulSoup(response, 'html.parser')
        self.assertEqual(
            len(index.select(".travis_env")), 0, "Sha should not be shown when not connected"
        )

        # Update the REPO !
        response = self.client.patch("/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit/token")
        self.assertEqual(response.status_code, 401, "Request Forbidden")

        with self.logged_in(access_token="nbiousndegoijubdognlksdngndsgmngds"):
            response = self.client.get("/repo/PerseusDl/canonical-latinLit").data.decode()
            index = BeautifulSoup(response, 'html.parser')
            travis_env1 = index.select(".travis_env")
            self.assertEqual(len(travis_env1), 1, "Sha should be shown when not connected")
            self.assertEqual(len(travis_env1[0].text), 40)

            # Update the REPO !
            response = loads(self.client.patch("/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit/token")\
                .data.decode())
            self.assertEqual(response, {"status": True})

            response = self.client.get("/repo/PerseusDl/canonical-latinLit").data.decode()
            index = BeautifulSoup(response, 'html.parser')
            travis_env2 = index.select(".travis_env")
            self.assertEqual(len(travis_env2), 1, "Sha should be shown when not connected")
            self.assertEqual(len(travis_env2[0].text), 40)
            self.assertNotEqual(travis_env1[0].text, travis_env2[0].text, "Sha should be different")