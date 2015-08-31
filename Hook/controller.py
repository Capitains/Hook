from flask import redirect, jsonify

import hmac
import hashlib
from uuid import uuid4

import Hook.models.github
from Hook.models.user import User

class Controller(object):
    """ Controller base object

    :param api: Github API DB
    :param db: MongoDB Engine

    """
    def __init__(self, api, db, g, session):
        self.api = api
        self.db = db
        self.g = g
        self.session = session

    def before_request(self):
        pass


class UserCtrl(Controller):
    """ User oriented controller

    """
    def before_request(self):
        if 'user_id' in self.session:
            self.g.user = User.objects.get(uuid=self.session['user_id'])

    def login(self, url_redirect):
        """ Login the user using github API

        :param url_redirect: Url to redirect to
        :return: redirect(url_redirect)
        """
        if self.session.get('user_id', None) is None:
            return self.api.authorize(scope=",".join(["user:email", "repo:status", "admin:repo_hook", "read:org"]))
        return redirect(url_redirect)

    def authorize(self, access_token, request, success, error):
        """ Callback uri of Github API to signin/up a user

        :param access_token: Access token sent by github
        :param request: request informations
        :param success: success redirect uri
        :param error: error redirect uri
        :return: redirect()
        """
        if access_token is None:
            return redirect(error)

        user = User.objects(github_access_token=access_token)

        if len(user) == 0:
            # Make a call to the API
            more = self.api.get("user", params={"access_token": access_token})
            user = User(
                uuid=str(uuid4()),
                github_access_token=access_token,
                mail=more["email"],
                git_id=more["id"],
                login=more["login"]
            )
        else:
            user = user.first()

        user.github_access_token = access_token
        user.save()

        self.session['user_id'] = user.uuid
        return redirect(success)

    def fetch(self):
        pass

    def logout(self, url_redirect):
        """ Logout the user and redirect to a specific url

        :param url_redirect: Url to redirect to
        :return: redirect(url_redirect)
        """
        self.session.pop('user_id', None)
        return redirect(url_redirect)

    def manage(self):
        pass


class TestCtrl(Controller):
    """ Controller base object

    :param signature: Signature Secret Key
    :param api: Github API DB
    :param db: MongoDB Engine

    """
    def __init__(self, signature, **kwargs):
        super(TestCtrl, self).__init__(**kwargs)
        self.signature = signature

    def user(self, repository=None, required=False):
        """
            Raise 404 if user is required
            :return:
        """
        user = None
        if hasattr(self.g, "user") and self.g.user is not None:
            user = self.g.user
        elif repository is not None:
            pass  # Get it from the repository

        if not user and required:
            raise ValueError()
        return user

    def generate_informations(self, repository):
        """

        :param repository:
        :return:
        """
        status = self.api.get(
            "repos/{owner}/{name}/commits".format(owner=repository.owner, name=repository.name),
            params={"sha": "master", "per_page": "1"}
        )
        if len(status) == 0:
            return "error", "No commits available", 404

        sha = status[0]["sha"]
        ref = "master"
        creator = status[0]["author"]["login"]
        guid = str(uuid4())
        url = status[0]["url"]

        return ref, creator, sha, url, guid

    def generate(self, user, repository, ref=None, creator=None, sha=None, url=None, uuid=None):
        """ Generate a test on the machine

        :param user: Name of the user
        :type user: str
        :param repository: Name of the repository
        :type repository: str
        :param ref: branch to be tested
        :type ref: str
        """
        avatar = "https://avatars.githubusercontent.com/{0}".format(creator)
        repo = Hook.models.github.Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)
        status = 200

        if creator is None:  # sha and url should be None
            informations = self.generate_informations(repo)
            if len(informations) == 3:
                return informations
            else:
                ref, creator, sha, url, uuid = informations

        test = Hook.models.github.RepoTest.Get_or_Create(uuid, repo.owner, repo.name, ref)
        test.user = creator
        test.gravatar = avatar
        test.sha = sha
        test.save()

        self.dispatch(test)

        return "success", "Test launched", status

    def dispatch(self, test):
        pass

    def check_signature(self, body, hub_signature):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :param hub_signature: Signature sent by github
        :return:
        """
        signature = 'sha1={0}'.format(hmac.new(self.signature, body, hashlib.sha1).hexdigest())
        if signature == hub_signature:
            return True
        else:
            return False

    def handle_payload(self, request, headers):
        """ Handle a payload call from Github

        :param request:
        :param headers:
        :return:
        """
        status, message, status = "error", "Webhook query is not handled", 300
        creator, sha, ref, url, do = None, None, None, None, None

        signature = headers.get("X-Hub-Signature")
        if not self.check_signature(request.data, signature):
            return jsonify(
                status="error",
                message="Signature check did not pass"
            )

        payload = request.get_json(force=True)
        guid = headers.get("X-GitHub-Delivery")
        event = headers.get("X-GitHub-Event")
        username, repository = tuple(payload["repository"]["full_name"].split("/"))
        if event in ["push", "pull_request"]:
            if event == "push":
                creator = payload["head_commit"]["committer"]["username"]
                sha = payload["head_commit"]["id"]
                url = payload["compare"]
                ref = payload["ref"]
                do = True
            elif event == "pull_request" and payload["action"] in ["reopened", "opened", "synchronize"]:
                creator = payload["pull_request"]["user"]["login"]
                url = payload["pull_request"]["url"]
                sha = payload["pull_request"]["head"]["sha"]
                ref = payload["number"]
                do = True
            if do:
                status, message = self.generate(
                    username,
                    repository,
                    ref,
                    creator,
                    sha,
                    url,
                    uuid=guid
                )

        return jsonify(status=status, message=message)

    def status(self):
        pass

    def cancel(self):
        pass

    def result(self):
        pass