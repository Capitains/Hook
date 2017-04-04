from time import sleep


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
        branch="master",
        travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262544",
        travis_build_id="27",
        travis_user="sonofmun",
        travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
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
        }
    )
    sleep(0.05)
    # Create second test
    test2_units = {key:val for key, val in former_unit.items()}
    test2_units["data/tlg0015/tlg001/tlg0015.tlg001.opp-grc1.xml"] = True
    test2_units["data/tlg0015/tlg001/__cts__.xml"] = False
    test2_units["data/tlg0015/tlg002/__cts__.xml"] = False
    del test2_units["data/tlg0015/__cts__.xml"]
    test2, *_ = latinLit.register_test(
        branch="issue-45",
        travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262555",
        travis_build_id="28",
        travis_user="sonofmun",
        travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
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
        }
    )
    sleep(0.05)

    class Mokes(object):
        def __init__(self, db, latinLit):
            self.latinLit = latinLit
            self.db = db
            self.models = models
            self.ponteineptique = ponteineptique
            self.greekLit = greekLit

        def add_repo_to_pi(self):
            self.ponteineptique.repositories.append(self.latinLit)
            self.ponteineptique.repositories.append(self.greekLit)
            db.session.commit()

        def make_new_latinLit_test(self, session, coverage=99.85):
            test3, *_ = self.models.Repository.query.filter(
                models.Repository.owner == "PerseusDl",
                models.Repository.name == "canonical-latinLit"
            ).first().register_test(
                branch="master",
                travis_uri="https://travis-ci.org/PerseusDl/canonical-latinLit/builds/216262588",
                travis_build_id="29",
                travis_user="sonofmun",
                travis_user_gravatar="sonofmun@yahoooooooooooooooooooooooooooooooooooooo.com",
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
                }
            )
            session.commit()
    db.session.commit()
    return Mokes(db, latinLit)
