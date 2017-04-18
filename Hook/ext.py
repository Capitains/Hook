from flask import Blueprint, url_for, request, render_template, g, session, redirect, \
    jsonify, send_from_directory, Markup
from werkzeug.exceptions import NotFound, Forbidden, BadRequest
from flask_github import GitHub
from flask_login import LoginManager, current_user, login_required, login_user
from flask_sqlalchemy import SQLAlchemy

from pkg_resources import resource_filename
import re
import hmac
import hashlib
import json

from Hook.models import model_maker


class HookUI(object):
    ROUTES = [
        ('/', "r_index", ["GET"]),
        ('/login', "r_login", ["GET"]),
        ('/login/error', "r_login_error", ["GET"]),
        ('/logout', "r_logout", ["GET"]),

        ('/api/github/callback', "r_github_oauth", ["GET"]),

        ('/repo/<owner>/<repository>', "r_repository", ["GET"]),
        ('/repo/<owner>/<repository>/<uuid>', "r_repository_test", ["GET"]),

        ("/api/hook/v2.0/user/repositories", "r_api_user_repositories", ["GET", "POST"]),
        ("/api/hook/v2.0/user/repositories/<owner>/<repository>", "r_api_user_repository_switch", ["PUT"]),
        ("/api/hook/v2.0/user/repositories/<owner>/<repository>", "r_api_hooktest_endpoint", ["POST"]),
        ('/api/hook/v2.0/user/repositories/<owner>/<repository>/history', "r_api_repo_history", ["GET"]),
        ('/api/hook/v2.0/user/repositories/<owner>/<repository>/token', "r_api_update_token", ["PATCH"]),

        ('/api/hook/v2.0/badges/<owner>/<repository>/texts.svg', "r_repo_texts_count", ["GET"]),
        ('/api/hook/v2.0/badges/<owner>/<repository>/metadata.svg', "r_repo_metadata_count", ["GET"]),
        ('/api/hook/v2.0/badges/<owner>/<repository>/words.svg', "r_repo_words_count", ["GET"]),
        ('/api/hook/v2.0/badges/<owner>/<repository>/coverage.svg', "r_repo_badge_coverage", ["GET"]),


        ("/favicon.ico", "r_favicon", ["GET"]),
        ("/favicon/<icon>", "r_favicon_specific", ["GET"])
    ]

    route_login_required = [
        "r_api_user_repositories",
        "r_api_user_repository_switch",
        "r_api_update_token"
    ]

    FILTERS = [
        "f_nice_link_to_source",
        'f_btn'
    ]

    VERBOSE = re.compile("(>>>>>>[^>]+)")
    PR_FINDER = re.compile("pull\/([0-9]+)\/head")

    def __init__(self,
         prefix="", database=None, github=None, login=None,
         remote=None, github_secret=None, hooktest_secret=None,
         static_folder=None, template_folder=None, app=None, name=None,
         commenter_github_access_token=None
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
        :param commenter_github_access_token: Access Token of the User who posts comment
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
        self.hooktest_secret = hooktest_secret or "super_secret!"
        self.prefix = prefix
        self.commenter_github_access_token = commenter_github_access_token

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
        return self.url_for(".index")

    def r_github_oauth(self, *args, **kwargs):
        """ GitHub oauth route
        """
        def func(access_token):
            next_uri = request.args.get('next') or self.url_for('.index')
            return self.authorize(access_token, request, success=next_uri, error=self.url_for(".login_error"))

        authorize = self.api.authorized_handler(func)
        return authorize(*args, **kwargs)

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

    def r_api_hooktest_endpoint(self, owner, repository):
        """ Route HookTest endpoint

        :param owner: Name of the owner
        :param repository: Name of the repository
        """
        return jsonify(self.handle_hooktest_log(request=request, owner=owner, repository=repository))

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

    def r_api_update_token(self, owner, repository):
        """ Regenerate the Travis Environment Token

        :param owner: Owner
        :param repository: Repository
        :return: Json Status
        """
        repo = self.Models.Repository.get_or_raise(owner, repository)
        return jsonify({"status": repo.regenerate_travis_env(current_user, self.db.session)})

    def r_favicon(self):
        return self.r_favicon_specific()

    def r_favicon_specific(self, icon="favicon.ico"):
        return send_from_directory(resource_filename("Hook", "data/static/favicon"), icon, mimetype='image/vnd.microsoft.icon')

    @staticmethod
    def f_nice_link_to_source(test):
        """ Transform a git formatted reference into something more human readable

        :param test: Current Test
        :return: Human readable branch name
        """
        repo = test.repository_dyn
        if test.event_type == "push":
            return Markup(
                '<a href="https://github.com/{owner}/{repository}/commit/{full_sha}">@{sha}</a>'.format(
                    owner=repo.owner,
                    repository=repo.name,
                    full_sha=test.sha,
                    sha=test.sha[:8]
                )
            )
        else:
            return Markup(
                '<a href="https://github.com/{owner}/{repository}/pull/{pr_id}">PR #{pr_id}</a>'.format(
                    owner=repo.owner,
                    repository=repo.name,
                    pr_id=test.source
                )
            )

    @staticmethod
    def f_btn(boolean):
        """ Return btn bs3 class depending on status

        :param boolean: Boolean
        :return: "btn-success" and "btn-danger" depending on boolean
        """
        if boolean:
            return "btn-success"
        return "btn-danger"

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

    def handle_hooktest_log(self, owner, repository, request):
        """ Handle data received from Redis server commands

        :param owner: Name of the owner
        :param repository: Name of the repository
        :param request: request object
        :return: Status Code
        """

        if not request.data:
            raise BadRequest(description="No post data")
        elif request.content_type != "application/json":
            raise BadRequest(description="Data is not json encoded")

        repo = self.Models.Repository.get_or_raise(owner, repository)
        if self.check_hooktest_signature(request.data, repo, request.headers.get("HookTest-Secure-X")) is False:
            raise Forbidden(description="Signature is not right")

        repo = self.Models.Repository.get_or_raise(owner, repository)
        data = json.loads(request.data.decode('utf-8'))

        # Format of expected data :
        try:
            kwargs = dict(
                # Information about the commit
                source=data["source"],
                travis_uri=data["build_uri"],
                travis_build_id=data["build_id"],
                sha=data["commit_sha"],
                event_type=data["event_type"],

                # Information about the test
                texts_total=data["texts_total"],
                texts_passing=data["texts_passing"],
                metadata_total=data["metadata_total"],
                metadata_passing=data["metadata_passing"],
                coverage=data["coverage"],
                nodes_count=data["nodes_count"],
                units=data["units"],
            )
            if "words_count" in data:
                kwargs["words_count"] = data["words_count"]
        except KeyError as E:
            raise BadRequest(description="Missing parameter " + str(E))

        # Information about the User
        kwargs.update(self.get_user_information_from_github(kwargs, owner, repository))

        test, diff = repo.register_test(**kwargs)
        if data["event_type"] == "push":
            uri = "repos/{owner}/{repository}/commits/{sha}/comments".format(
                owner=owner, repository=repository, sha=test.sha
            )
        else:
            uri = "repos/{owner}/{repository}/issues/{sha}/comments".format(
                owner=owner, repository=repository, sha=test.source
            )

        # Commenting
        if diff is not None:
            self.comment(test, diff, uri=uri)
        return {
            "status": "success",
            "link": self.url_for(".repository_test", owner=owner, repository=repository, uuid=test.uuid)
        }

    def get_user_information_from_github(self, data, owner, repository):
        """ Retrieve information about the current user

        :param data: Current data built for RepoTest
        :param owner:  Name of the owner
        :param repository: Name of the repository
        :return: Dictionary with user(name) key and avatar key
        """
        slug = owner+"/"+repository
        if data["event_type"] == 'pull_request':
            status = self.api.get(
                "repos/{slug}/pulls/{_id}".format(
                    slug=slug,
                    _id=data["source"]),
                    params={
                        'access_token': self.commenter_github_access_token
                    }
            )
            return {"user": status['user']['login'], "avatar": status['user']['avatar_url']}
        elif data["event_type"] == 'push':
            status = self.api.get(
                "repos/{slug}/commits/{_id}".format(
                    slug=slug,
                    _id=data["sha"]
                ),
                params={
                    'access_token': self.commenter_github_access_token
                }
            )
            return {"user": status['author']['login'], "avatar": status['author']['avatar_url']}

    def make_hooktest_signature(self, body, secret):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :param secret: Secret specific to the repository
        :return: Signature for HookTest
        """
        return '{0}'.format(
            hmac.new(
                bytes(secret, encoding="utf-8"),
                body,
                hashlib.sha1
            ).hexdigest()
        )

    def check_hooktest_signature(self, body, repo, hook_signature):
        """ Check the signature sent by a request with the body

        :param body: Raw body of the request
        :param repo: Repository for which we check the signature
        :param hook_signature: Signature sent by github
        :return: Equality indicator
        """
        if self.make_hooktest_signature(body, repo.travis_env) == hook_signature:
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

    def words_count_badge(self, username, reponame, language=None, uuid=None):
        """ Return the necessary information to build a text count badge

        :param username: Name of the repository owner
        :param reponame: Name of the repository
        :param language: Language we want wordcount from
        :param uuid: Id of the test we want the name from
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
        :param branch: Branch or Source (Pull Request) to filter on
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
                    self.Models.RepoTest.source == branch
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

    def comment(self, test, diff, uri):
        """ Takes care of sending information to github API through the comment / status API

        :param test: The test currently running or finished
        :param diff: The diff
        :param uri: Address where we want to post
        :return:
        """
        repo = test.repository_dyn

        data = {
          "body": """{}

*[Hook UI build recap]({})*
""".format(
              test.table(diff, mode="md"),
              self.url_for(".repository_test", owner=repo.owner, repository=repo.name, uuid=test.uuid, _external=True)
           ),
        }

        params = {"access_token": self.commenter_github_access_token}

        output = self.api.post(uri, data=data, params=params)

        test.comment_uri = output["html_url"]
        self.db.session.add(test)
        self.db.session.commit()

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

        more = self.api.get("user", params={"access_token": access_token})

        user = self.Models.User.query.filter(self.Models.User.git_id == str(more["id"]), self.Models.User.login == more["login"]).first()

        if user is None:
            # Make a call to the API
            kwargs = dict(git_id=str(more["id"]), login=more["login"])
            if "email" in more:
                kwargs["email"] = more["email"]

            user = self.Models.User(
                **kwargs
            )
            self.db.session.add(user)

        user.github_access_token = access_token
        self.db.session.commit()

        login_user(user)
        return redirect(success)

    def fetch_repositories(self, method):
        """ Fetch repositories of a user

        :param method: Method that was used : POST->refresh, GET->list
        :return: List of repository in json
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

    def login(self, url_redirect):
        """ Login the user using github API

        :param url_redirect: Url to redirect to
        :return: redirect(url_redirect)
        """
        if self.session.get('user_id', None) is None:
            return self.api.authorize(scope=",".join(["user:email", "repo:status", "admin:repo_hook", "read:org"]))
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

    def url_for(self, route, **kwargs):
        with self.app.app_context():
            return url_for(route, **kwargs)

    def filter_or_404(self, model, *ident):
        rv = model.query.filter(*ident).first()
        if rv is None:
            raise NotFound(description="Unknown repository")
        return rv
