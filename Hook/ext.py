from flask import Blueprint, url_for, request, render_template, g, Markup, session, redirect, \
    jsonify, send_from_directory, abort
from werkzeug.exceptions import NotFound
from flask_github import GitHub
from flask_login import LoginManager, current_user, login_required, login_user
from flask_sqlalchemy import SQLAlchemy

from pkg_resources import resource_filename
import re
import hmac
import hashlib
import json
import requests
from uuid import uuid4

from Hook.models import model_maker
from Hook.common import slugify


class HookUI(object):
    ROUTES = [
        ('/', "r_index", ["GET"]),
        ('/login', "r_login", ["GET"]),
        ('/login/error', "r_login_error", ["GET"]),
        ('/logout', "r_logout", ["GET"]),

        ('/api/github/callback', "r_github_oauth", ["GET"]),
        ('/api/github/payload', "r_github_payload", ["GET", "POST"]),
        ("/api/hooktest", "r_api_hooktest_endpoint", ["POST"]),

        ('/repo/<owner>/<repository>', "r_repository", ["GET", "POST"]),
        ('/repo/<owner>/<repository>/<uuid>', "r_repository_test", ["GET"]),

        ("/api/hook/v2.0/user/repositories", "r_api_user_repositories", ["GET", "POST"]),
        ("/api/hook/v2.0/user/repositories/<owner>/<repository>", "r_api_user_repository_switch", ["PUT"]),
        ('/api/hook/v2.0/user/repositories/<owner>/<repository>/history', "r_api_repo_history", ["GET", "DELETE"]),

        ('/api/hook/v2.0/badges/<owner>/<repository>/texts.svg', "r_repo_texts_count", ["GET"]),
        ('/api/hook/v2.0/badges/<owner>/<repository>/metadata.svg', "r_repo_metadata_count", ["GET"]),
        ('/api/hook/v2.0/badges/<owner>/<repository>/words.svg', "r_repo_words_count", ["GET"]),
        ('/api/hook/v2.0/badges/<owner>/<repository>/coverage.svg', "r_repo_badge_coverage", ["GET"]),


        ("/favicon.ico", "r_favicon", ["GET"]),
        ("/favicon/<icon>", "r_favicon_specific", ["GET"])
    ]

    route_login_required = [
        "r_api_user_repositories",
        "r_api_user_repository_switch"
    ]

    FILTERS = [
        "f_nice_ref",
        "f_nice_branch",
        'f_slugify',
        'f_checked',
        'f_btn',
        'f_success_class',
        "f_ctsized"
    ]

    VERBOSE = re.compile("(>>>>>>[^>]+)")
    PR_FINDER = re.compile("pull\/([0-9]+)\/head")

    def __init__(self,
         prefix="", database=None, github=None, login=None,
         remote=None, github_secret=None, hooktest_secret=None,
         static_folder=None, template_folder=None, app=None, name=None
    ):
        """ Initiate the class

        :param prefix: Prefix on which to install the extension
        :param database: Mongo Database to use
        :type database: MongoEngine
        :param github: GitHub extension for doing requests
        :type github: GitHub
        :param login: Login extension
        :type login: LoginManager
        :param static_folder: New static folder
        :param template_folder: New template folder
        :param app: Application on which to register
        :param name: Name to use for the blueprint
        """
        self.__g = None

        self.app = app
        self.name = name
        self.blueprint = None
        self.Models = None

        self.db = database
        self.api = github
        self.login_manager = login

        self.remote = remote
        self.github_secret = github_secret
        self.hooktest_secret = hooktest_secret
        self.prefix = prefix

        self.static_folder = static_folder
        if not self.static_folder:
            self.static_folder = resource_filename("Hook", "data/static")

        self.template_folder = template_folder
        if not self.template_folder:
            self.template_folder = resource_filename("Hook", "data/templates")

        if self.name is None:
            self.name = __name__

        if self.app:
            self.init_app(app=app)

    def before_request(self):
        """ Before request function for the Blueprint
        """
        g.user = current_user

    def init_app(self, app):
        """ Initiate the extension on the application

        :param app: Flask Application
        :return: Blueprint for HookUI registered in app
        :rtype: Blueprint
        """

        if not self.app:
            self.app = app

        if not self.db:
            self.db = SQLAlchemy(app)
        if not self.api:
            self.api = GitHub(app)
        if not self.login_manager:
            self.login_manager = LoginManager(app)

        # Register token getter for github
        self.api.access_token_getter(self.github_token_getter)

        # Register the user loader for LoginManager
        self.login_manager.user_loader(self.login_manager_user_loader)

        self.init_blueprint()

        # Generate Instance models
        self.Models = model_maker(self.db)

        return self.blueprint

    def init_blueprint(self):
        """ Properly generates the blueprint, registering routes and filters and connecting the app and the blueprint

        """
        self.blueprint = Blueprint(
            self.name,
            self.name,
            url_prefix=self.prefix,
            template_folder=self.template_folder,
            static_folder=self.static_folder,
            static_url_path='/static/{0}'.format(self.name)
        )

        # Register routes
        for url, name, methods in HookUI.ROUTES:
            view_func = getattr(self, name)
            if name in self.route_login_required:
                view_func = login_required(view_func)
            self.blueprint.add_url_rule(
                url,
                view_func=view_func,
                endpoint=name[2:],
                methods=methods
            )
        # Register

        for _filter in HookUI.FILTERS:
            self.app.jinja_env.filters[
                _filter.replace("f_", "")
            ] = getattr(self.__class__, _filter)

        # Register the before request
        self.blueprint.before_request(self.before_request)

        self.app.register_blueprint(self.blueprint)

    def login_manager_user_loader(self, user_id):
        """ Load a user

        :param user_id: User id
        :type user_id: int
        :return: User or None
        :rtype: User
        """
        return self.Models.User.query.get(int(user_id))

    def github_token_getter(self):
        """ Get the github token

        :return: User github access token or None
        """
        if current_user is not None:
            return current_user.github_access_token

    def r_login(self):
        """ Route for login
        """
        return self.login(self.url_for(".index"))

    def r_logout(self):
        """ Route for logout
        """
        return self.logout(self.url_for(".index"))

    def r_login_error(self):
        """ Route for logout
        """
        return request.query_string

    def r_github_oauth(self, *args, **kwargs):
        """ GitHub oauth route
        """
        def func(access_token):
            next_uri = request.args.get('next') or self.url_for('.index')
            return self.authorize(access_token, request, success=next_uri, error=self.url_for(".login_error"))

        authorize = self.api.authorized_handler(func)
        return authorize(*args, **kwargs)

    def r_github_payload(self):
        """ GitHub payload route
        """
        return self.handle_payload(
            request,
            request.headers
        )

    def r_index(self):
        """ Index route
        """
        return render_template("index.html")

    def r_repository(self, owner, repository):
        """ Route for the repository test history, statistics and settings

        :param owner: Name of the owner
        :param repository: Name of the repository
        """
        kwargs = self.read_repo(owner, repository, request)
        return render_template(
            'repo.html',
            **kwargs
        )

    def r_repository_test(self, owner, repository, uuid):
        """ Route for a test report

        :param owner: Name of the owner
        :param repository: Name of the repository
        :param uuid: UUID of the test
        """
        kwargs, status, header = self.repo_report(owner, repository, uuid)
        if status == 200:
            return render_template("report.html", **kwargs)
        else:
            return kwargs, status, header

    def r_api_hooktest_endpoint(self):
        """ Route HookTest endpoint
        """
        return "", self.handle_hooktest_log(request), {}

    def r_api_user_repositories(self):
        """ Route fetching user repositories
        """
        return self.fetch_repositories(request.method)

    def r_api_user_repository_switch(self, owner, repository):
        """ Route for toggling github webhook

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        content, status_code = self.toggle_repo(owner, repository)
        r = jsonify(content)
        r.status_code = status_code
        return r

    def r_repo_texts_count(self, owner, repository):
        """ Get a Text Count Badge for a repository

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, kwargs, status, header = self.texts_count_badge(owner, repository, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
        if response:
            return render_template(response, **kwargs), status, header

    def r_repo_metadata_count(self, owner, repository):
        """ Get a Metadata Count Badge for a repository

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, kwargs, status, header = self.metadata_count_badge(
            owner, repository,
            branch=request.args.get("branch"), uuid=request.args.get("uuid")
        )
        if response:
            return render_template(response, **kwargs), status, header

    def r_repo_words_count(self, owner, repository):
        """ Get a Words Count Badge for a repository

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, kwargs, status, header = self.words_count_badge(
            owner, repository,
            language=request.args.get("lang"),
            uuid=request.args.get("uuid")
        )
        if response:
            return render_template(response, **kwargs), status, header

    def r_repo_badge_coverage(self, owner, repository):
        """ Get a Badge for a repo

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, kwargs, status, header = self.coverage_badge(owner, repository, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
        if response:
            return render_template(response, **kwargs), status, header

    def r_api_test_generate_route(self, owner, repository):
        """ Generate a test on the machine

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        return self.generate(
            owner,
            repository,
            callback_url=self.url_for(".api_hooktest_endpoint", _external=True),
            check_user=True
        )

    def r_api_repo_history(self, owner, repository):
        """ Return json history of previous tests

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        if request.args.get("uuid"):
            return self.repo_report(
                owner,
                repository,
                uuid=request.args.get("uuid"),
                json=True
            )
        else:
            return self.history(owner, repository)

    def r_favicon(self):
        return self.r_favicon_specific()

    def r_favicon_specific(self, icon="favicon.ico"):
        return send_from_directory(resource_filename("Hook", "data/static/favicon"), icon, mimetype='image/vnd.microsoft.icon')

    @staticmethod
    def f_nice_ref(branch, commit):
        """ Transform a git formatted reference into something more human readable or returns part of commit sha

        :param branch: Github Reference
        :param commit: Commit SHA
        :return: Human readable reference
        """
        print(branch, commit)
        if HookUI.PR_FINDER.match(branch):
            return "PR #{0}".format(branch.strip("pull/").strip("/head"))
        return commit[0:8]

    @staticmethod
    def f_nice_branch(branch):
        """ Transform a git formatted reference into something more human readable

        :param branch: Github Reference
        :return: Human readable branch name
        """
        if HookUI.PR_FINDER.match(branch):
            return "PR #{0}".format(branch.strip("pull/").strip("/head"))
        else:
            return branch.split("/")[-1]

    @staticmethod
    def f_slugify(string):
        """ Slugify filter

        :return: Slugified string
        """
        if not string:
            return ""
        return slugify(string)

    @staticmethod
    def f_checked(boolean):
        """ Check a checkbox if boolean is true

        :param boolean: Boolean
        :return: "checked" if boolean is True
        """
        if boolean:
            return " checked "
        return ""

    @staticmethod
    def f_btn(boolean):
        """ Return btn bs3 class depending on status

        :param boolean: Boolean
        :return: "btn-success" and "btn-danger" depending on boolean
        """
        if boolean:
            return "btn-success"
        return "btn-danger"

    @staticmethod
    def f_success_class(status):
        """ Return success or failed depending on boolean

        :param status: Status
        :return: Success or fail
        """
        string = ""
        if status is True:
            string = "success"
        elif status is False:
            string = "failed"
        return string

    @staticmethod
    def f_ctsized(cts_tuple):
        """ Join a tuple of text

        :param cts_tuple: Tuple representing the number of texts cts compliant and the total number of text
        :type cts_tuple: (int, int)
        :return: Stringified tuple
        """
        return "{0}/{1}".format(*cts_tuple)

    """
        CONTROLLER FUNCTIONS
    """

    def read_repo(self, owner, repository, request):
        """ Read the repository tests

        :param owner: Name of the owner of the repository
        :param repository: Name of the repository
        :param request: Request information
        :return: Repository informations with a list of tests (completed and running separated)

        .. todo:: Pagination & Moving the post to the route

        """

        start, end = 0, 20
        repository = self.Models.Repository.get_or_raise(owner=owner, name=repository)

        if request.method == "POST" and current_user.is_authenticated and repository.has_rights(current_user):
            repository.config(request.form)

        # PAGINATION !!!
        tests = repository.tests.order_by(self.Models.RepoTest.run_at.desc()).paginate()


        return {
            "repository": repository,
            "tests": tests
        }

    def toggle_repo(self, owner, repository):
        """ Route for toggling writing on repository

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        repository = self.Models.Repository.get_or_raise(owner=owner, name=repository)
        if repository is None:
            return {"error": "Unknown repository"}, 404
        else:
            return {"status": repository.switch_active(current_user)}, 200

    def repo_report(self, owner, repository, uuid, json=False):
        """ Generate data for repository report

        :param owner: Name of the owner of the repository
        :param repository: Name of the repository
        :param uuid: Unique Identifier of the test
        :param json: Format in JSON
        :return: Response containing the Report
        """

        repository = self.Models.Repository.get_or_raise(owner=owner, name=repository)
        test = repository.get_test(uuid)

        if json is True:
            dic = {
                'reponame': 'canonical-latinLit',
                'username': 'PerseusDl'
            }
            dic.update(test.dict)
            return jsonify(dic)
        else:
            return {
                "repository": repository,
                "test": test
            }, 200, {}

    def repo_report_unit(self, owner, repository, uuid, unit):
        """ Generate data for repository report for a single unit

        :param owner: Name of the owner of the repository
        :param repository: Name of the repository
        :param uuid: Unique Identifier of the test
        :param unit: Identifier of the Unit
        :return: Report for a specific unit
        """

        repository = self.m_Repository.objects.filter_or_404(owner__iexact=owner, name__iexact=repository)
        if unit == "all":
            test = self.m_RepoTest.objects.filter_or_404(repository=repository, uuid=uuid)
            report = self.m_RepoTest.report(owner, repository, repo_test=test)
        else:
            test = self.m_RepoTest.objects(
                repository=repository, uuid=uuid
            ).first().units.filter(
                path=unit
            ).first()
            if test is None:
                return "", 404
            report = self.m_DocTest.report(test)

        return report

    def generate_informations(self, repository):
        """ Generate informations for a user generated build

        :param repository: Repository for which a test should be run
        :type repository: Repository
        :return: Reference, Creator identifier, Commit Sha, URL on Github for the repository, GitHub UUID
        """
        status = self.api.get(
            "repos/{owner}/{name}/commits".format(owner=repository.owner, name=repository.name),
            params={"sha": "master", "per_page": "1"}
        )
        if len(status) == 0:
            return "error", "No commits available", 404

        sha = status[0]["sha"]
        ref = "refs/heads/master"
        if "author" in status[0]:
            creator = status[0]["author"]["login"]
        else:
            creator = status[0]["commit"]["author"]["name"]
        guid = str(uuid4())
        url = status[0]["html_url"]

        return ref, creator, sha, url, guid

    def generate(self, username, reponame, callback_url=None, ref=None, creator=None, sha=None, url=None, uuid=None, check_branch=False, check_user=True):
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
        :param check_branch: If set to True, should check against repo.master_pr
        """
        repo = self.m_Repository.objects.filter_or_404(owner__iexact=username, name__iexact=reponame)

        if check_user:
            if hasattr(g, "user") and not repo.isWritable(g.user):
                resp = jsonify(status="error", message="You are not an owner of the repository", uuid=None)
                return resp

        if check_branch == True and repo.master_pr == True:
            if not HookUI.PR_FINDER.match(ref) and not ref.endswith("master"):
                response = jsonify(status="ignore", message="Test ignored because this is not a pull request nor a push to master")
                return response

        if creator is None:  # sha and url should be None
            informations = self.generate_informations(repo)
            if len(informations) == 3:
                return informations
            else:
                ref, creator, sha, url, uuid = informations

        running_test = self.m_RepoTest.objects(branch=ref, user=creator, sha=sha, repository=repo, link=url, status__in=["queued", "downloading", "downloading", "pending"])
        if len(running_test) > 0:
            return json.dumps({"message": "Test already running", "status": "error"}), 200

        avatar = "https://avatars.githubusercontent.com/{0}".format(creator)

        test = self.m_RepoTest.Get_or_Create(
            uuid=uuid,
            repository=repo,
            branch=ref,
            user=creator,
            gravatar=avatar,
            sha=sha,
            link=url
        )

        status, message = self.dispatch(test, callback_url)
        self.comment(test)

        return jsonify(status=status, message=message, uuid=uuid)

    def dispatch(self, test, callback_url):
        """ Dispatch a test to the redis queue

        :param test: The test to be sent
        :param callback_url: URL to send log to
        """

        params = {
            "repository": test.repository.full_name,
            "ping": callback_url,
            "verbose": test.verbose,
            "console": False,
            "uuid" : test.uuid,
            "scheme": test.scheme,
            "branch": test.branch
        }
        params = bytes(json.dumps(params), encoding="utf-8")
        response = requests.put(self.remote, data=params, headers={'content-type': 'application/json', "HookTest-Secure-X" : self.make_hooktest_signature(params)})
        infos = response.json()

        if infos["status"] == "queued":
            test.update(hash=infos["job_id"], status="queued")
            return "success", "Test launched"
        else:
            return infos["status"], "Error while dispatching test"

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
        test = self.m_RepoTest.objects(uuid=uuid).exclude("units.logs").exclude("units.text_logs").first()
        if not test:
            return 404
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
            update = {}
            if "units" in data:
                _units = []
                for unit in data["units"]:
                    _units.append(self.m_DocTest(
                        at=unit["at"],
                        path=unit["name"],
                        status=unit["status"],
                        coverage=unit["coverage"]
                    ))

                    for text in unit["logs"]:
                        _units[-1].text_logs.append(self.m_DocLogs(text=text))

                    for test_name, test_status in unit["units"].items():
                        _units[-1].logs.append(self.m_DocUnitStatus(
                            title=test_name,
                            status=test_status
                        ))
                update["push_all__units"] = _units

            if "coverage" in data:
                update["coverage"] = data["coverage"]
                update["status"] = data["status"]

            if len(update) > 0:
                test.update(**update)

        if "status" in data and data["status"] in ["success", "error", "failed"]:
            test.reload()
            self.comment(test)
        return 200

    def make_hooktest_signature(self, body):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :return: Signature for HookTest
        """
        return '{0}'.format(
            hmac.new(
                bytes(self.hooktest_secret, encoding="utf-8"),
                body,
                hashlib.sha1
            ).hexdigest()
        )

    def check_hooktest_signature(self, body, hook_signature):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :param hook_signature: Signature sent by github
        :return: Equality indicator
        """
        if self.make_hooktest_signature(body) == hook_signature:
            return True
        else:
            return False

    def check_github_signature(self, body, hub_signature):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :param hub_signature: Signature sent by github
        :return: Equality Indicator
        """
        signature = 'sha1={0}'.format(hmac.new(bytes(self.github_secret, encoding="utf-8"), body, hashlib.sha1).hexdigest())
        if signature == hub_signature:
            return True
        else:
            return False

    def handle_payload(self, request, headers):
        """ Handle a payload call from Github [Gonna need to change]

        :param request: Request sent by github
        :param headers: Header of the GitHub Request
        :param callback_url: URL to use as a callback for HOOK
        :return: Response
        """
        status, message, code = "error", "Webhook query is not handled", 200
        creator, sha, ref, url, do = None, None, None, None, None
        pull_request = False

        signature = headers.get("X-Hub-Signature")
        if not self.check_github_signature(request.data, signature):
            response = jsonify(
                status="error",
                message="Signature check did not pass"
            )
            response.status_code = 300
            return response

        payload = request.get_json(force=True)
        event = headers.get("X-GitHub-Event")
        username, repository = tuple(payload["repository"]["full_name"].split("/"))
        if event in ["push", "pull_request"]:
            if event == "push":
                creator = payload["head_commit"]["committer"]["username"]
                sha = payload["head_commit"]["id"]
                url = payload["compare"]
                ref = payload["ref"]
                pull_request = False
                do = True
            elif event == "pull_request" and payload["action"] in ["reopened", "opened", "synchronize"]:
                creator = payload["pull_request"]["user"]["login"]
                url = payload["pull_request"]["html_url"]
                sha = payload["pull_request"]["head"]["sha"]
                ref = "pull/{0}/head".format(payload["number"])
                do = True
                pull_request = True
            if do:
                response = self.generate(
                    username,
                    repository,
                    callback_url=self.url_for(".api_hooktest_endpoint", _external=True),
                    creator=creator,
                    sha=sha,
                    url=url,
                    ref=ref,
                    uuid=str(uuid4()),
                    check_branch=pull_request
                )
                return response

        response = jsonify(status=status, message=message)
        response.status_code = code
        return response

    def words_count_badge(self, username, reponame, language=None, uuid=None):
        """ Return the necessary information to build a text count badge

        :param username: Name of the repository owner
        :param reponame: Name of the repository
        :return: (Template, Kwargs, Status Code, Headers)
        :rtype: (str, dict, int, dict)
        """
        repo = self.get_repo_test(username, reponame, uuid=uuid)

        if len(repo.words_count) == 0:
            raise NotFound(description="No words count available")

        if language is None:
            cnt = sum([wc.count for wc in repo.words_count])
            language = "Words"
        else:
            wc = [wc for wc in repo.words_count if wc.lang == language]
            if len(wc) == 0:
                raise NotFound(description="Unknown language")
            else:
                cnt = wc[0].count

        template = "svg/wordcount.xml"
        return template, {"language": language, "cnt": cnt}, 200, \
                {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def texts_count_badge(self, username, reponame, branch=None, uuid=None):
        """ Return the necessary information to build a text count badge

        :param username: Name of the repository owner
        :param reponame: Name of the repository
        :param branch: Name of the branch
        :param uuid: Travis Build Id
        :return: (Template, Kwargs, Status Code, Headers)
        :rtype: (str, dict, int, dict)
        """
        repo = self.get_repo_test(username, reponame, branch, uuid)

        cnt, total = repo.texts_passing, repo.texts_total
        template = "svg/object_count.xml"
        return template, {"object_name": "Texts", "cnt": cnt, "total": total}, 200, \
                {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def metadata_count_badge(self, username, reponame, branch=None, uuid=None):
        """ Return the necessary information to build a metadata count badge

        :param username: Name of the repository owner
        :param reponame: Name of the repository
        :param branch: Name of the branch
        :param uuid: Travis Build Id
        :return: (Template, Kwargs, Status Code, Headers)
        :rtype: (str, dict, int, dict)
        """
        repo = self.get_repo_test(username, reponame, branch, uuid)

        cnt, total = repo.metadata_passing, repo.metadata_total
        template = "svg/object_count.xml"
        return template, {"object_name": "Metadata", "cnt": cnt, "total": total}, 200, \
                {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def coverage_badge(self, username, reponame, branch=None, uuid=None):
        """ Create a coverage badge

        :param username: Name of the repository owner
        :param reponame: Name of the repository
        :param branch: Name of the branch
        :param uuid: Travis Build Id
        :return: (Template, Kwargs, Status Code, Headers)
        :rtype: (str, dict, int, dict)
        """
        repo = self.get_repo_test(
            owner=username,
            name=reponame,
            branch=branch,
            uuid=uuid
        )

        if repo.coverage > 90.0:
            template = "svg/build.coverage.success.xml"
        elif repo.coverage > 75.0:
            template = "svg/build.coverage.acceptable.xml"
        else:
            template = "svg/build.coverage.failure.xml"

        return template, {"score": repo.coverage}, 200, {'Content-Type': 'image/svg+xml; charset=utf-8'}

    def get_repo_test(self, owner, name, branch=None, uuid=None):
        """ Get a repository test given generic informations

        :param owner: Name of the repository Owner
        :type owner: str
        :param name: Repository Name
        :type name: str
        :param branch: Branch to filter on
        :type uuid: str
        :param uuid: Travis Build Number
        :type uuid: str
        :return: Repoitory Test
        :rtype: RepoTest
        """
        if uuid is not None or branch is not None:
            repo = self.Models.RepoTest.query.join(
                self.Models.Repository, self.Models.Repository.uuid == self.Models.RepoTest.repository
            ).filter(
                    self.Models.Repository.owner == owner,
                    self.Models.Repository.name == name
            )

            if branch:
                repo = repo.filter(
                    self.Models.RepoTest.branch == branch
                )
            if uuid:
                repo = repo.filter(
                    self.Models.RepoTest.travis_build_id == uuid
                )
            repo = repo.order_by(self.Models.RepoTest.run_at.desc())
            repo = repo.first()
            if repo is None:
                raise NotFound(description="Unknown repository's test")
        else:
            repo = self.filter_or_404(
                self.Models.Repository,
                self.Models.Repository.owner == owner,
                self.Models.Repository.name == name
            ).last_master_test
        return repo

    def history(self, username, reponame):
        """ Return the history of a repo

        :param username:
        :param reponame:
        :return:
        """
        repository = self.Models.Repository.get_or_raise(owner=username, name=reponame)
        pagination = repository.tests.order_by(self.Models.RepoTest.run_at.desc()).paginate()
        history = {
            "username": username,
            "reponame": reponame,
            "logs": [
                {
                    "run_at": event.run_at,
                    "uuid": event.uuid,
                    "coverage": event.coverage
                }
                for event in pagination.items
            ]
        }
        if pagination.has_next or pagination.has_prev:
            history["cursor"] = {}
            if pagination.has_next:
                history["cursor"]["next"] = self.url_for(
                    ".api_repo_history",
                    owner=username, repository=reponame, page=pagination.next_num
                )
            if pagination.has_prev:
                history["cursor"]["prev"] = self.url_for(
                    ".api_repo_history",
                    owner=username, repository=reponame, page=pagination.prev_num
                )
            history["cursor"]["last"] = self.url_for(
                ".api_repo_history",
                owner=username, repository=reponame, page=pagination.pages
            )
        return jsonify(**history)

    def comment(self, test):
        """ Takes care of sending information to github API through the comment / status API

        :param test: The test currently running or finished
        :return:
        """
        repo = test.repository
        uri = "repos/{owner}/{repo}/statuses/{sha}".format(owner=repo.owner, repo=repo.name, sha=test.sha)
        if test.status == "error":
            state = "error"
            sentence = "Test cancelled or ran into an error"
        elif test.status == "success":
            state = "success"
            sentence = "Full repository is cts compliant"
        elif test.status == "failed":
            state = "failure"
            sentence = "{0:.2f}% of unit tests passed".format(test.coverage)
        else:
            state = "pending"
            sentence = "Currently testinself.g..."

        data = {
          "state": state,
          "target_url": self.url_for(".repository_test", owner=repo.owner, repository=repo.name, uuid=test.uuid, _external=True),
          "description": sentence,
          "context": "continuous-integration/capitains-hook"
        }

        params = {}
        if not hasattr(self.g, "user"):
            user = repo.authors[0]
            access_token = user.github_access_token
            params = {"access_token": access_token}

        self.api.post(uri, data=data, params=params)

    def login(self, url_redirect):
        """ Login the user using github API

        :param url_redirect: Url to redirect to
        :return: redirect(url_redirect)
        """
        if self.session.get('user_id', None) is None:
            return self.api.authorize(scope=",".join(["user:email", "repo:status", "admin:repo_hook", "read:org"]))
        return redirect(url_redirect)


    """
        USER CONTROLLER
    """
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

        user = self.Models.User.query.filter(self.Models.User.github_access_token == access_token).first()

        if user is None:
            # Make a call to the API
            more = self.api.get("user", params={"access_token": access_token}).json()
            kwargs = dict(git_id=more["id"], login=more["login"])
            if "email" in more:
                kwargs["email"] = more["email"]

            user = self.Models.User(
                github_access_token=access_token,
                **kwargs
            )
            self.db.session.add(user)
            self.db.session.commit()

        login_user(user)
        return redirect(success)

    def fetch_repositories(self, method):
        """ Fetch repositories of a user

        :param method:
        :return:
        """
        response = []
        if method == "POST":
            # We clear the old authors
            current_user.remove_authorship()

            repositories = self.api.get(
                "user/repos",
                params={
                    "affiliation": "owner,collaborator,organization_member",
                    "access_token": current_user.github_access_token
                },
                all_pages=True
            )

            for repo in repositories:
                owner = repo["owner"]["login"]
                name = repo["name"]
                repo = self.Models.Repository.find_or_create(owner, name, _commit_on_create=False)
                current_user.repositories.append(repo)
                response.append(repo)
            self.db.session.commit()
        elif method == "GET":
            response = current_user.repositories

        return jsonify({"repositories": [repo.dict() for repo in response]})

    def logout(self, url_redirect):
        """ Logout the user and redirect to a specific url

        :param url_redirect: Url to redirect to
        :return: redirect(url_redirect)
        """
        self.session.pop('user_id', None)
        del g.user
        return redirect(url_redirect)

    @property
    def session(self):
        """ Flask Session
        """
        with self.app.app_context():
            return session

    @property
    def g(self):
        """ G Flask APP global information
        """
        if not self.__g:
            with self.app.app_context():
                self.g = g

        return self.__g

    @g.setter
    def g(self, value):
        self.__g = value

    @property
    def domain(self):
        """ Domain URL of the current app
        """
        with self.app.app_context():
            return url_for("", _external=True)

    @property
    def callback_url_hooktest_endpoint(self):
        """ Callback URL use for retrieving data from the HookTest service
        """
        return self.url_for(".api_hooktest_endpoint", _external=True)

    def url_for(self, route, **kwargs):
        with self.app.app_context():
            return url_for(route, **kwargs)

    def filter_or_404(self, model, *ident):
        rv = model.query.filter(*ident).first()
        if rv is None:
            raise NotFound(description="Unknown repository")
        return rv

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

