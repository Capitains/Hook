import datetime

from json import loads

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
                "username": "PerseusDl"
            }
        )
