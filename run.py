from flask import Flask, redirect
from flask_login import LoginManager, login_user
from flask_sqlalchemy import SQLAlchemy
import flask_github

from logging import getLogger
from contextlib import contextmanager
import re
import datetime
import sys
import os
import requests_mock

from tests.make_moke import make_moke
from tests.github_fixtures import make_fixture
from tests.baseTest import github_user

from Hook.ext import HookUI

try:
    os.remove("Hook/test1.db")
except:
    """ Something !"""

app = Flask("Hook")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test1.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GITHUB_CLIENT_ID'] = "github_client_id"
app.config['GITHUB_CLIENT_SECRET'] = "github_client_secret"
app.config["SECRET_KEY"] = 'super secret key'
db = SQLAlchemy(app)

# Mokes
hook = HookUI(
    database=db, github=flask_github.GitHub(app=app), login=LoginManager(app=app),
    commenter_github_access_token=os.environ.get("HOOKUI")
)


def mock_authorize(token, request, success, error):
    with app.app_context():
        u = Models.User.query.filter(Models.User.github_access_token == "nbiousndegoijubdognlksdngndsgmngds")\
            .first()
        login_user(u)
        return redirect(success)

hook.authorize = mock_authorize
hook.init_app(app)
Models = hook.Models
db.create_all()
Mokes = make_moke(db, Models)
fixtures = make_fixture(Mokes.ponteineptique.github_access_token)

extraMocks = [
    (
        "get",
        "https://api.github.com/user/repos",
        dict(
            json=fixtures['./tests/fixtures/repos_ponteineptique.response.json'][0],
            headers=fixtures['./tests/fixtures/repos_ponteineptique.response.json'][1]
        )
     ),
    (
        "get",
        re.compile("https://api.github.com/user/repos\?.*page=2"),
        dict(
            json=fixtures['./tests/fixtures/repos_ponteineptique.page2.response.json'][0],
            headers=fixtures['./tests/fixtures/repos_ponteineptique.page2.response.json'][1]
        )
     )
]
logger = getLogger(__name__)


@contextmanager
def logged_in(access_token="yup", extra_mocks=None):
    if extra_mocks is None:
        extra_mocks = []
    code = 'yeah'
    github_resp = 'access_token=%s' % access_token
    github_matcher = re.compile('github.com/')
    github_usermatcher = re.compile('https://api.github.com/user')
    headers = {'Content-Type': 'application/json'}

    with requests_mock.Mocker() as m:
        m.post(github_matcher, text=github_resp)
        m.get(github_usermatcher, json=github_user)
        for verb, url, kwargs in extra_mocks:
            m.register_uri(verb, re.compile(url), **kwargs)

        # at this point we are logged in
        try:
            yield
        finally:
            # logging out
            print("Hell")


if __name__ == "__main__":
    with logged_in(access_token="nbiousndegoijubdognlksdngndsgmngds", extra_mocks=extraMocks):
        Mokes.add_repo_to_pi()
        test = Mokes.make_new_latinLit_test(db.session, coverage=55.0)
        test = Mokes.make_new_latinLit_PR(db.session, coverage=55.0)
        Mokes.make_lots_of_tests(
            45, db.session, Mokes.latinLit,
            coverage_ends_at=75.0, datetime_starts_at=datetime.datetime(2017, 4, 5, 7, 4, 22, tzinfo=None)
        )

        Mokes.latinLit.active = True
        test.run_at = test.run_at + datetime.timedelta(3, 3)

        db.session.commit()
        print("Login through http://localhost:5000/api/github/callback")
        app.run(debug=True)
