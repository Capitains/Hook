import datetime

import re
from json import loads, dumps
from copy import deepcopy
from tests.baseTest import BaseTest


class TestAPI(BaseTest):

    def test_repository_api(self):
        self.Mokes.test1.run_at = datetime.datetime(2017, 4, 5, 7, 4, 22, tzinfo=None)
        self.Mokes.test2.run_at = datetime.datetime(2017, 4, 5, 7, 4, 27, tzinfo=None)
        self.db.session.commit()
        response = self.client.get("/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit/history")
        self.assertEqual(
            loads(response.data.decode()),
            {
                "logs": [
                    {
                        "coverage": 99.85,
                        "run_at": "Wed, 05 Apr 2017 07:04:27 GMT",
                        "uuid": 2
                    },
                    {
                        "coverage": 99.79,
                        "run_at": "Wed, 05 Apr 2017 07:04:22 GMT",
                        "uuid": 1
                    }
                ],
                "reponame": "canonical-latinLit",
                "username": "PerseusDl"
            }
        )

    def test_repository_api_pagination(self):
        self.Mokes.make_lots_of_tests(
            45, self.db.session, self.Mokes.greekLit,
            coverage_ends_at=75.0, datetime_starts_at=datetime.datetime(2017, 4, 5, 7, 4, 22, tzinfo=None)
        )
        response = self.client.get("/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history")
        resp_json = loads(response.data.decode())
        self.assertEqual(
            resp_json["logs"][0],
            {
                "coverage": 75.0,
                "run_at": "Fri, 07 Apr 2017 04:04:22 GMT",
                "uuid": 47
            },
            "Last test should be there"
        )
        self.assertEqual(
            resp_json["cursor"],
            {
                "next": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=2",
                "last": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=3"
            }
        )
        response = self.client.get("/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=2")
        resp_json = loads(response.data.decode())
        self.assertEqual(
            resp_json["logs"][0],
            {
                "coverage": 65.0,
                "run_at": "Thu, 06 Apr 2017 08:04:22 GMT",
                "uuid": 27
            },
            "25th test should be there"
        )
        self.assertEqual(
            resp_json["cursor"],
            {
                "next": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=3",
                "prev": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=1",
                "last": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=3"
            }
        )
        response = self.client.get("/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=3")
        resp_json = loads(response.data.decode())
        self.assertEqual(
            resp_json["logs"][0],
            {
                "coverage": 55.0,
                "run_at": "Wed, 05 Apr 2017 12:04:22 GMT",
                "uuid": 7
            },
            "Fifth test should be there"
        )
        self.assertEqual(
            resp_json["cursor"],
            {
                "prev": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=2",
                "last": "/api/hook/v2.0/user/repositories/PerseusDl/canonical-greekLit/history?page=3"
            }
        )

    def test_repository_api_specific_id(self):
        self.Mokes.test2.run_at = datetime.datetime(2017, 4, 5, 7, 4, 27, tzinfo=None)
        self.db.session.commit()
        response = self.client.get("/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit/history?uuid=2")
        self.assertEqual(
            loads(response.data.decode()),
            {
                "coverage": 99.85,
                'metadata_passing': 718,
                'metadata_total': 720,
                'nodes_count': 113179,
                'texts_passing': 636,
                'texts_total': 637,
                'words_count': {'eng': 125, 'ger': 1088, 'lat': 1050},
                "reponame": "canonical-latinLit",
                "username": "PerseusDl",
                'comment_uri': 'https://github.com/PerseusDL/canonical-latinLit/commit/7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments',
            }
        )

    @property
    def pr_push(self):
        return {
          "build_uri": "https://travis-ci.org/Capitains/HookTest/builds/219210604",
          "build_id": "212",
          "event_type": "pull_request",
          "commit_sha": "24880f5078f0c1e84653b5fa8e6c6985fc411d57",
          "source": "5",

          "user": "ponteineptique",
          "avatar": "https://avatars2.githubusercontent.com/u/1929830",

          "texts_total": 475,
          "texts_passing": 440,
          "metadata_total": 475,
          "metadata_passing": 440,
          "coverage": 76.01,
          "nodes_count": 745650,
          "units": self.Mokes.units
    }

    def test_repository_failures(self):
        # Without secret
        reply = self.client.post(
            "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit",
            data=dumps(deepcopy(self.pr_push)),
            content_type='application/json'
        )
        self.assertEqual(reply.status_code, 403, "Signature is not right")
        self.assertIn("Signature is not right", reply.data.decode())

        # Without data
        reply = self.client.post(
            "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit",
            content_type='application/json'
        )
        self.assertEqual(reply.status_code, 400, "Bad Request")
        self.assertIn("No post data", reply.data.decode())

        # Without json data
        reply = self.client.post(
            "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit",
            data=dumps(deepcopy(self.pr_push))
        )
        self.assertEqual(reply.status_code, 400, "Bad Request")
        self.assertIn("Data is not json encoded", reply.data.decode())

        # Without json data
        reply = self.client.post(
            "/api/hook/v2.0/user/repositories/PerseusDl/canonical-farsiLit",
            data=dumps(deepcopy(self.pr_push)),
            content_type='application/json',
            headers={
                "HookTest-Secure-X": self.hook.make_hooktest_signature(
                    dumps(deepcopy(self.pr_push)).encode(),
                    secret=self.Mokes.latinLit.travis_env
                )
            }
        )
        self.assertEqual(reply.status_code, 404, "Unknown Repository")
        self.assertIn("Unknown Repository", reply.data.decode())
        # Missing parameter
        d = dumps({k: v for k, v in self.pr_push.items() if k not in ["source"]})
        reply = self.client.post(
            "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit",
            data=d,
            content_type='application/json',
            headers={
                "HookTest-Secure-X": self.hook.make_hooktest_signature(
                    d.encode(),
                    secret=self.Mokes.latinLit.travis_env
                )
            }
        )
        self.assertEqual(reply.status_code, 400, "Unknown Repository")
        self.assertIn("Missing parameter 'source'", reply.data.decode())

    def test_repository_pr_success(self):
        # Without secret
        with self.mocks([
                (
                    "post",
                    re.compile("api.github.com/repos/PerseusDl/canonical-latinLit/issues/5/comments"),
                    dict(
                        json=self.fixtures['./tests/fixtures/pr.comment.response.json'][0],
                        headers=self.fixtures['./tests/fixtures/pr.comment.response.json'][1],
                        status_code=201
                    )
                 ),
                (
                    "get",
                    re.compile("api.github.com/repos/PerseusDl/canonical-latinLit/pulls/5"),
                    dict(
                        json=self.fixtures['./tests/fixtures/commit.pull_request.response.json'][0],
                        status_code=200
                    )
                )
        ]):
            reply = self.client.post(
                "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit",
                data=dumps(self.pr_push),
                content_type='application/json',
                headers={
                    "HookTest-Secure-X": self.hook.make_hooktest_signature(
                        dumps(self.pr_push).encode(),
                        secret=self.Mokes.latinLit.travis_env
                    )
                }
            )
            self.assertEqual(reply.status_code, 200, "Data is all right !")
            self.assertEqual(
                {'status': 'success', 'link': '/repo/PerseusDl/canonical-latinLit/3'},
                loads(reply.data.decode())
            )
            reply = loads(self.client.get(
                "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit/history?uuid=3"
            ).data.decode())
            self.assertEqual(
                reply["comment_uri"],
                'https://github.com/PerseusDl/canonical-latinLit/issues/5#issuecomment-1'
            )

    @property
    def comment_push(self):
        return {
          "build_uri": "https://travis-ci.org/Capitains/HookTest/builds/219210604",
          "build_id": "212",
          "event_type": "push",
          "commit_sha": "24880f5078f0c1e84653b5fa8e6c6985fc411d57",
          "source": "issue-5",

          "user": "ponteineptique",
          "avatar": "https://avatars2.githubusercontent.com/u/1929830",

          "texts_total": 475,
          "texts_passing": 440,
          "metadata_total": 475,
          "metadata_passing": 440,
          "coverage": 76.01,
          "nodes_count": 745650,
          "units": self.Mokes.units
    }

    def test_commit_comment_api(self):
        with self.mocks([
                (
                    "post",
                    re.compile("api.github.com/repos/PerseusDl/canonical-latinLit/commits/24880f5078f0c1e84653b5fa8e6c6985fc411d57/comments"),
                    dict(
                        json=self.fixtures['./tests/fixtures/commit.comment.response.json'][0],
                        headers=self.fixtures['./tests/fixtures/commit.comment.response.json'][1],
                        status_code=201
                    )
                 ),
                (
                    "get",
                    re.compile("api.github.com/repos/PerseusDl/canonical-latinLit/commits/24880f5078f0c1e84653b5fa8e6c6985fc411d57"),
                    dict(
                        json=self.fixtures['./tests/fixtures/commit.push.response.json'][0],
                        status_code=200
                    )
                )
        ]):
            #https://avatars2.githubusercontent.com/u/1929830?v=3
            reply = self.client.post(
                "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit",
                data=dumps(self.comment_push),
                content_type='application/json',
                headers={
                    "HookTest-Secure-X": self.hook.make_hooktest_signature(
                        dumps(self.comment_push).encode(),
                        secret=self.Mokes.latinLit.travis_env
                    )
                }
            )
            self.assertEqual(reply.status_code, 200, "Data is all right !")
            self.assertEqual(
                {'status': 'success', 'link': '/repo/PerseusDl/canonical-latinLit/3'},
                loads(reply.data.decode())
            )
            reply = loads(self.client.get(
                "/api/hook/v2.0/user/repositories/PerseusDl/canonical-latinLit/history?uuid=3"
            ).data.decode())
            self.assertEqual(
                reply["comment_uri"],
                'https://github.com/PerseusDl/canonical-latinLit/commit/6dcb09b5b57875f334f61aebed695e2e4193db5e#commitcomment-1'
            )