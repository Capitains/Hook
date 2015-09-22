import math
import hmac
import hashlib
import json
from uuid import uuid4

from flask import redirect, jsonify
from rq import Queue
from rq.job import Job, JobStatus
from redis import Redis

from HookTest.test import cmd
from Hook.models import User, Repository, RepoTest, DocLogs, DocTest, DocUnitStatus


class Controller(object):
    """ Controller base object

    :param api: Github API DB
    :param db: MongoDB Engine
/tests
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
            user.save()
        else:
            user = user.first()

        self.session['user_id'] = user.uuid
        return redirect(success)

    def fetch(self, method):
        """ Fetch repositories of a user

        :param method:
        :return:
        """
        response = []
        if hasattr(self.g, "user") and self.g.user:
            if method == "POST":
                # We clear the old authors
                self.g.user.remove_authorship()

                repositories = self.api.get(
                    "user/repos",
                    params={
                        "affiliation": "owner,collaborator,organization_member",
                        "access_token": self.g.user.github_access_token
                    },
                    all_pages=True
                )

                for repo in repositories:
                    owner = repo["owner"]["login"]
                    name = repo["name"]
                    repo = self.g.user.addto(owner=owner, name=name)
                    response.append(repo)
            elif method == "GET":
                response = self.g.user.repositories

        return jsonify({"repositories" : [repo.dict() for repo in response]})

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
    @staticmethod
    def slice(elements, start, max=None):
        """ Return a sublist of elements, starting from index {start} with a length of {max}

        :param elements: List of elements to slice
        :type elements: list
        :param start: Starting element (0-based Index)
        :type start: int
        :param max: Maximum number of elements to return
        :type max: int

        :return: (Sublist, Starting index of the sublist, end_index)
        :rtype: (list, int, int)
        """
        length = len(elements)
        real_index = start + 1
        if length < real_index:
            return [], length, 0
        else:
            if max is not None and max + start < length:
                return elements[start:max+start], start, max+start
            else:
                return elements[start:], start, length - 1


    def __init__(self, signature, redis, hooktest_path, hooktest_secret, workers, domain, **kwargs):
        super(TestCtrl, self).__init__(**kwargs)
        self.signature = signature
        self.redis = redis
        self.hooktest_path = hooktest_path
        self.domain = domain
        self.workers = workers
        self.hooktest_secret = hooktest_secret

    def read_repo(self, owner, repository, request):
        """ Read the repository tests

        :param owner:
        :param repository:
        :param request:
        :return:
        .. todo:: Pagination
        """

        start, end = 0, 20
        repository = Repository.objects.get_or_404(owner__iexact=owner, name__iexact=repository)

        if request.method == "POST" and hasattr(self.g, "user") and self.g.user in repository.authors:
            repository.config(request.form)

        # PAGINATION !!!
        tests = RepoTest.objects(
            repository=repository
        ).exclude(
            "units"
        )
        for test in tests:
            test.branch = test.branch.split("/")[-1]

        done = [test for test in tests if test.finished]
        running = [test for test in tests if test.finished == False]

        for r in running:
            if r.total > 0:
                r.percent = int(r.tested / r.total * 100)
            else:
                r.percent = 0

        return {
            "repository": repository,
            "tests": done,
            "running": running
        }

    def repo_report(self, owner, repository, uuid, start=0, limit=None, json=False):
        """ Generate data for repository report

        :param owner:
        :param repository:
        :param uuid:
        :param start: Starting item (0 based)
        :type int:
        :param limit: Number of logs line to show
        :type limit: int
        :param json: Returns json
        :type json: bool
        :return:
        """

        repository = Repository.objects.get_or_404(owner__iexact=owner, name__iexact=repository)
        test = RepoTest\
            .objects(repository=repository, uuid=uuid)\
            .exclude("units.text_logs")\
            .first()

        if json is True:
            return jsonify(test.units_status())
        else:
            return {
                "repository": repository,
                "test": test
            }, 200, {}

    def repo_report_unit(self, owner, repository, uuid, unit):
        """ Generate data for repository report

        :param owner:
        :param repository:
        :param uuid:
        :param start: Starting item (0 based)
        :type int:
        :param limit: Number of logs line to show
        :type limit: int
        :param json: Returns json
        :type json: bool
        :return:
        """

        repository = Repository.objects.get_or_404(owner__iexact=owner, name__iexact=repository)
        if unit == "all":
            test = RepoTest.objects.get_or_404(repository=repository, uuid=uuid)
        else:
            test = DocTest.objects.get_or_404(path=unit,repository=repository, uuid=uuid)
        report = RepoTest.report(owner, repository, repo_test=test)

        return jsonify(report)

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
        """ Generate informations for a user generated build

        :param repository: Repository for which a test should be run
        :type repository: Repository
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
        url = status[0]["html_url"]

        return ref, creator, sha, url, guid

    def generate(self, username, reponame, callback_url=None, ref=None, creator=None, sha=None, url=None, uuid=None):
        """ Generate a test on the machine

        :param username: Name of the user
        :type username: str
        :param reponame: Name of the repository
        :type reponame: str
        :param callback_url: URL to send log to
        :param ref: branch to be tested
        :type ref: str
        :param creator: Person responsible for starting the test
        :param sha: SHA of the commit
        :param url: URL of the resource
        :param uuid: UUID to use
        """
        repo = Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)
        status = 200

        if creator is None:  # sha and url should be None
            informations = self.generate_informations(repo)
            if len(informations) == 3:
                return informations
            else:
                ref, creator, sha, url, uuid = informations

        avatar = "https://avatars.githubusercontent.com/{0}".format(creator)

        test = RepoTest.Get_or_Create(
            uuid=uuid,
            repository=repo,
            branch=ref,
            user=creator,
            gravatar=avatar,
            sha=sha,
            link=url
        )

        self.dispatch(test, callback_url)

        return jsonify(status="success", msg="Test launched", uuid=uuid)

    def dispatch(self, test, callback_url):
        """ Dispatch a test to the redis queue

        :param test: The test to be sent
        :param callback_url: URL to send log to
        """

        redis_conn = Redis(self.redis)
        q = Queue(connection=redis_conn)
        job = q.enqueue_call(
            func=cmd,
            kwargs={
                "path": self.hooktest_path,
                "repository": test.repository.full_name,
                "ping": callback_url,
                "verbose": test.verbose,
                "console": False,
                "uuid" : test.uuid,
                "workers": self.workers,
                "secret": self.hooktest_secret,
                "scheme": test.scheme
            },
            timeout=3600,
            result_ttl=86400
        )
        test.update(hash=job.get_id(), status="inqueue")

    def handle_hooktest_log(self, request):
        """ Handle data received from Redis server commands

        :param request: request object
        :return: Status Code
        """

        if not request.data or not request.headers.get("HookTest-UUID"):
            return 404
        elif self.check_hooktest_signature(request.data, request.headers.get("HookTest-Secure-X")) is False:
            return 401

        # Now we get the repo
        uuid = request.headers.get("HookTest-UUID")
        test = RepoTest.objects.get_or_404(uuid=uuid)
        data = json.loads(request.data.decode('utf-8'))

        # If the test just started
        if "status" in data:
            test.update(status=data["status"])
        if "message" in data:
            test.update(error_message=data["message"])

        if "files" in data and "inventories" in data and "texts" in data:
            test.update(
                texts=data["texts"],
                cts_metadata=data["inventories"]
            )
        else:
            # If we have units, we have single logs to save
            if "units" in data:
                for unit in data["units"]:
                    unit_mongo = DocTest(
                        at=unit["at"],
                        path=unit["name"],
                        status=unit["status"],
                        coverage=unit["coverage"]
                    )

                    for text in unit["logs"]:
                        unit_mongo.text_logs.append(DocLogs(text=text))

                    for test_name, test_status in unit["units"].items():
                        unit_mongo.logs.append(DocUnitStatus(
                            title=test_name,
                            status=test_status
                        ))

                    test.units.append(unit_mongo)

            if "coverage" in data:
                test.coverage = data["coverage"]
                test.status = data["status"]

            test.save()

        return 200

    def check_hooktest_signature(self, body, hook_signature):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :param hub_signature: Signature sent by github
        :return:
        """
        signature = '{0}'.format(
            hmac.new(
                bytes(self.hooktest_secret, encoding="utf-8"),
                body,
                hashlib.sha1
            ).hexdigest()
        )
        if signature == hook_signature:
            return True
        else:
            return False

    def check_github_signature(self, body, hub_signature):
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
        status, message, code = "error", "Webhook query is not handled", 300
        creator, sha, ref, url, do = None, None, None, None, None

        signature = headers.get("X-Hub-Signature")
        if not self.check_github_signature(request.data, signature):
            response = jsonify(
                status="error",
                message="Signature check did not pass"
            )
            response.status_code = 300
            return response

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

        response = jsonify(status=status, message=message)
        response.status_code = status
        return response


    def cancel(self, owner, repository, uuid=None):
        """ Cancel a test

        :param owner:
        :param repository:
        :param uuid:
        :return:
        """
        if uuid is None:
            return "Unknown test", 404, {}
        repo = Repository.objects.get_or_404(username__iexact=owner, name__iexact=repository)
        test = RepoTest.objects.get_or_404(repository=repo, uuid__iexact=uuid)
        test.update(status=False, total=0, tested=0)
        return jsonify(cancelled=True)


    def link(self, owner, repository, callback_url):
        """ Set Github to start or stop pinging the current repository

        :param owner:
        :param repository:
        :param callback_url: URL for callback
        :return: json
        """
        response = False

        if hasattr(self.g, "user") and self.g.user:
            repository = Repository.objects(
                authors__in=[self.g.user],
                owner__iexact=owner,
                name__iexact=repository
            )
            if len(repository) > 0:
                repository = repository.first()
                tested = not repository.tested
                repository.update(tested=tested)
                repository.reload()
                response = self.__make_link(repository, callback_url)

        return jsonify(status=response)

    def __make_link(self, repository, callback_url):
        """ Create or delete hooks on GitHub API

        :param repository: Repository to add or delete the hook from
        :type repository: Hook.models.github.Repository

        :returns: Active status
        """
        uri = "repos/{owner}/{repo}/hooks".format(owner=repository.owner, repo=repository.name)
        payload = self.domain + callback_url

        if repository.tested is True:
            # Create hooks
            hook_data = {
              "name": "web",
              "active": True,
              "events": [
                "push",
                "pull_request"
              ],
              "config": {
                "url": payload,
                "content_type": "json",
                "secret": self.signature
              }
            }
            service = self.api.post(uri, data=hook_data)
            if "id" in service:
                repository.update(hook_id=service["id"])
        else:
            if repository.hook_id is None:
                hooks = self.api.get(uri)
                hooks = [service for service in hooks if service["config"]["url"] == payload]
                if len(hooks) == 0:
                    uuid = None
                else:
                    uuid = hooks[0]["id"]
            else:
                uuid = repository.hook_id
            if uuid is not None:
                self.api.delete("repos/{owner}/{repo}/hooks/{id}".format(owner=repository.owner, repo=repository.name, id=uuid))

        return repository.tested

    def cts_badge(self, username, reponame, branch=None, uuid=None):
        """

        :param username:
        :param reponame:
        :param branch:
        :param uuid:
        :return:
        :return: (Template, Kwargs, Status Code, Headers)
        """
        repo = self.repo(
            owner=username,
            name=reponame,
            branch=branch,
            uuid=uuid
        )

        if not repo:
            return None, None, 404, {}

        cts, total = repo.ctsized()
        template = "svg/cts.xml"
        return template, {"cts": cts, "total": total}, 200, {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def status_badge(self, username, reponame, branch=None, uuid=None):
        """ Create a status badge

        :param username:
        :param reponame:
        :param branch:
        :param uuid:
        :return: (Template, Headers, Status Code)
        """
        repo = self.repo(
            owner=username,
            name=reponame,
            branch=branch,
            uuid=uuid
        )

        if not repo:
            return None, 404, {}
        else:
            template = "svg/build.{0}.xml".format(repo.status)

        return template, 200, {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def coverage_badge(self, username, reponame, branch=None, uuid=None):
        """ Create a status badge

        :param username:
        :param reponame:
        :param branch:
        :param uuid:
        :return: (Template, Kwargs, Status Code, Headers)
        """
        repo = self.repo(
            owner=username,
            name=reponame,
            branch=branch,
            uuid=uuid
        )

        if not repo or not repo.coverage:
            return "svg/build.coverage.unknown.xml", {}, 200, {'Content-Type': 'image/svg+xml; charset=utf-8'}

        score = math.floor(repo.coverage * 100) / 100

        if repo.coverage > 90:
            template = "svg/build.coverage.success.xml"
        elif repo.coverage > 75:
            template = "svg/build.coverage.acceptable.xml"
        else:
            template = "svg/build.coverage.failure.xml"

        return template, {"score": score}, 200, {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def repo(self, **kwargs):
        """ Helper to find repo
        :param kwargs:
        :return:
        """
        kwargs = {key+"__iexact":value for key, value in kwargs.items() if value is not None}
        repo_args = {key:value for key, value in kwargs.items() if key not in ["uuid__iexact", "branch__iexact"]}

        repo = Repository.objects.get_or_404(**repo_args)

        test_args = {"repository": repo}

        if "branch" in kwargs:
            test_args["branch__iexact"] = kwargs["branch__iexact"]

        if "uuid__iexact" in kwargs:
            test_args["uuid__iexact"] = kwargs["uuid__iexact"]
            test = RepoTest.objects(**test_args)
        else:
            test = RepoTest.objects(**test_args)

        if len(test) == 0:
            return None

        return test.first()

    def history(self, username, reponame):
        """ Return the history of a repo

        :param username:
        :param reponame:
        :return:
        """
        repository = Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)
        history = {
            "username" : username,
            "reponame" : reponame,
            "logs" : [
                {
                    "run_at" : event.run_at,
                    "uuid" : event.uuid,
                    "coverage" : event.coverage,
                    "ref" : event.branch,
                    "slug" : event.branch_slug
                }
                for event in RepoTest.objects(repository=repository)
            ]
        }
        return jsonify(**history)