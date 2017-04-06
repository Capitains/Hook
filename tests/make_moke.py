from time import sleep
import hashlib
from datetime import datetime, timedelta

def make_moke(db, models):
    former_unit = {
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
    ponteineptique = models.User(
        login="ponteineptique",
        email="leponteineptique@gyahoomail.com",
        git_id="GitSuperID",
        github_access_token="nbiousndegoijubdognlksdngndsgmngds"
    )
    db.session.add(ponteineptique)

    balmas = models.User(
        login="balmas",
        email="balmas@gyahoomail.com",
        git_id="GitSuperIDff",
        github_access_token="nbiousndegoijubdognlksdngndsgmngdsasdfasf"
    )
    db.session.add(balmas)

    latinLit = models.Repository(
        owner="PerseusDl",
        name="canonical-latinLit",
        active=False
    )
    db.session.add(latinLit)

    greekLit = models.Repository(
        owner="PerseusDl",
        name="canonical-greekLit",
        active=False
    )
    db.session.add(greekLit)
    db.session.commit()

    test, diff = latinLit.register_test(
        source="master",
        travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262544",
        travis_build_id="27",
        user="sonofmun",
        avatar="https://avatars0.githubusercontent.com/u/3787067?v=3&s=126",
        texts_total=637,
        texts_passing=630,
        metadata_total=720,
        metadata_passing=719,
        coverage=99.79,
        nodes_count=113179,
        units=former_unit,
        words_count={
            "eng": 125,
            "lat": 956
        },
        sha="7d3d6a0b62f0d244b684843c7546906d742013fd",
        comment_uri="https://github.com/PerseusDL/canonical-latinLit/commit/7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments"
    )
    sleep(0.05)
    # Create second test
    test2_units = {key:val for key, val in former_unit.items()}
    test2_units["data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml"] = True
    test2_units["data/tlg0015/tlg001/__cts__.xml"] = False
    test2_units["data/tlg0015/tlg002/__cts__.xml"] = False
    del test2_units["data/tlg0015/__cts__.xml"]
    test2, *_ = latinLit.register_test(
        source="issue-45",
        travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262555",
        travis_build_id="28",
        user="sonofmun",
        avatar="https://avatars0.githubusercontent.com/u/3787067?v=3&s=126",
        texts_total=637,
        texts_passing=636,
        metadata_total=720,
        metadata_passing=718,
        coverage=99.85,
        nodes_count=113179,
        units=test2_units,
        words_count={
            "eng": 125,
            "lat": 1050,
            "ger": 1088
        },
        sha="7d3d6a0b62f0d244b684843c7546906d742013fd",
        comment_uri="https://github.com/PerseusDL/canonical-latinLit/commit/7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments"
    )
    sleep(0.05)

    class Mokes(object):
        def __init__(self, db, latinLit):
            self.latinLit = latinLit
            self.db = db
            self.models = models
            self.ponteineptique = ponteineptique
            self.greekLit = greekLit
            self.test1 = test
            self.test2 = test2
            self.units = former_unit

        def add_repo_to_pi(self):
            self.ponteineptique.repositories.append(self.latinLit)
            self.ponteineptique.repositories.append(self.greekLit)
            db.session.commit()

        def make_new_latinLit_test(self, session, coverage=99.85):
            test3, *_ = self.models.Repository.query.filter(
                models.Repository.owner == "PerseusDl",
                models.Repository.name == "canonical-latinLit"
            ).first().register_test(
                source="master",
                travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262588",
                travis_build_id="29",
                user="sonofmun",
                avatar="https://avatars0.githubusercontent.com/u/3787067?v=3&s=126",
                texts_total=637,
                texts_passing=636,
                metadata_total=720,
                metadata_passing=718,
                coverage=coverage,
                nodes_count=113179,
                units=test2_units,
                words_count={
                    "eng": 125,
                    "lat": 1050,
                    "ger": 1088
                },
                sha="7d3d6a0b62f0d244b684843c7546906d742013fd",
                comment_uri="https://github.com/PerseusDL/canonical-latinLit/commit/7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments"
            )
            session.commit()
            return test3

        def make_lots_of_tests(
                self,
                number, session, target,
                coverage_ends_at=85.0, datetime_starts_at=None,

        ):
            if datetime_starts_at is None:
                datetime_starts_at = datetime(2017, 4, 5, 7, 4, 22, tzinfo=None)
            tests = []
            coverage_starts_at = coverage_ends_at - float(number)/2.0
            for i in range(1, number+1):
                sha = hashlib.sha1(str(i).encode('utf-8')).hexdigest()
                coverage = coverage_starts_at + i*0.5
                date = datetime_starts_at + timedelta(hours=i)

                test, _ = target.register_test(
                    source="issue-"+str(i),
                    travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262588",
                    travis_build_id=29+i,
                    user="sonofmun",
                    avatar="https://avatars0.githubusercontent.com/u/3787067?v=3&s=126",
                    texts_total=637,
                    texts_passing=636,
                    metadata_total=720,
                    metadata_passing=718,
                    coverage=coverage,
                    nodes_count=113179,
                    units=test2_units,
                    words_count={
                        "eng": 125,
                        "lat": 1050,
                        "ger": 1088+i
                    },
                    sha=sha,
                    comment_uri="https://github.com/PerseusDL/canonical-latinLit/commit/{}#all_commit_comments".format(sha),
                    _get_diff=False
                )
                test.run_at = date
                tests.append(test)
            session.commit()
            return tests

        def make_new_latinLit_PR(self, session, coverage=99.85):
            test3, *_ = self.models.Repository.query.filter(
                models.Repository.owner == "PerseusDl",
                models.Repository.name == "canonical-latinLit"
            ).first().register_test(
                source="55",
                event_type="pull_request",
                travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262588",
                travis_build_id="29",
                user="sonofmun",
                avatar="https://avatars0.githubusercontent.com/u/3787067?v=3&s=126",
                texts_total=637,
                texts_passing=636,
                metadata_total=720,
                metadata_passing=718,
                coverage=coverage,
                nodes_count=113179,
                units=test2_units,
                words_count={
                    "eng": 125,
                    "lat": 1050,
                    "ger": 1088
                },
                sha="7d3d6a0b62f0d244b684843c7546906d742013fd",
                comment_uri="https://github.com/PerseusDL/canonical-latinLit/commit/7d3d6a0b62f0d244b684843c7546906d742013fd#all_commit_comments"
            )
            session.commit()
            return test3

    db.session.commit()
    return Mokes(db, latinLit)
