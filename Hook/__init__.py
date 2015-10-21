from flask import Blueprint, url_for, request, render_template, g, Markup
from pkg_resources import resource_filename
import slugify as slugify_library
import re

class HookUI(object):
    ROUTES = [
        ('/', "r_index", ["GET"]),
        ('/login/form', "r_login", ["GET"]),
        ('/logout', "r_logout", ["GET"]),

        ('/api/github/callback', "r_github_oauth", ["GET"]),
        ('/api/github/payload', "r_github_payload", ["GET"]),
        ("/api/hooktest", "api_hooktest_endpoint", ["POST"]),

        ('/repo/<owner>/<repository>', "r_repository", ["GET", "POST"]),
        ('/repo/<owner>/<repository>/<uuid>', "r_repository_test", ["GET"]),

        ("/api/rest/v1.0/user/repositories", "r_api_user_repositories", ["GET", "POST"]),
        ("/api/rest/v1.0/user/repositories/<owner>/<name>", "r_api_user_repository_switch", ["PUT"]),

        ('/api/rest/v1.0/code/<owner>/<repository>/status.svg'"r_repo_badge_status", ["GET"]),
        ('/api/rest/v1.0/code/<owner>/<repository>/cts.svg'"r_repo_cts_status", ["GET"]),
        ('/api/rest/v1.0/code/<owner>/<repository>/coverage.svg'"r_repo_badge_coverage", ["GET"]),
        ('/api/rest/v1.0/code/<owner>/<repository>/test'"r_api_test_generate_route", ["GET"]),
        ('/api/rest/v1.0/code/<owner>/<repository>', "r_api_repo_history", ["GET", "DELETE"]),
        ('/api/rest/v1.0/code/<owner>/<repository>/unit', "r_api_repo_unit_history", ["GET"])
    ]

    FILTERS = [
        "r_nice_ref",
        "r_nice_branch",
        'r_slugify',
        'r_checked',
        'r_btn',
        'r_format_log',
        'r_tei',
        'r_epidoc',
        'r_success_class',
        "r_ctsized"
    ]

    VERBOSE = re.compile("(>>>>>>[^>]+)")
    PR_FINDER = re.compile("pull\/([0-9]+)\/head")

    def __init__(self,

                 static_folder=None, template_folder=None, app=None, name=None
                ):
        self.app = app
        self.name = name

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

    def init_app(self, app):
        pass

    def r_login(self):
        """ Route for login
        """
        with self.app.app_context():
            return self.login(url_for(".index"))

    def r_logout(self):
        """ Route for logout
        """
        with self.app.app_context():
            return self.logout(url_for(".index"))

    def r_github_oauth(self, access_token):
        """ GitHub oauth route
        """
        def func(self, access_token):
            with self.app.app_context():
                next_uri = request.args.get('next') or url_for('.index')
                return self.authorize(access_token, request, success=next_uri, error=url_for(".index"))

        self.authorized_handler(func)(access_token)

    def r_github_payload(self):
        """ GitHub payload route
        """
        return self.handle_payload(
            request,
            request.headers,
            callback_url=url_for(".api_hooktest_endpoint", _external=True)
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
        return self.fetch(request.method)

    def r_api_user_repository_switch(self, owner, repository):
        """ Route for toggling github webhook

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        with self.app.app_context():
            return self.link(owner, repository, url_for(".api_test_payload"))

    def r_repo_badge_status(self, owner, repository):
        """ Get a Badge for a repo

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, status, header = self.status_badge(owner, repository, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
        if response:
            return render_template(response), status, header
        else:
            return "", status, {}

    def r_repo_cts_status(self, owner, repository):
        """ Get a Badge for a repo

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, kwargs, status, header = self.cts_badge(owner, repository, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
        if response:
            return render_template(response, **kwargs), status, header
        else:
            return "", status, {}

    def r_repo_badge_coverage(self, owner, repository):
        """ Get a Badge for a repo

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        response, kwargs, status, header = self.coverage_badge(owner, repository, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
        if response:
            return render_template(response, **kwargs), status, header
        else:
            return "", status, {}

    def r_api_test_generate_route(self, owner, repository):
        """ Generate a test on the machine

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        with self.app.app_context():
            return self.generate(
                owner,
                repository,
                callback_url=url_for(".api_hooktest_endpoint", _external=True),
                check_user=True
            )

    def r_api_repo_history(self, owner, repository):
        """ Return json history of previous tests

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        if request.method == "DELETE":
            return self.cancel(owner, repository, uuid=request.args.get("uuid"))
        elif request.args.get("uuid"):
            return self.repo_report(
                owner,
                repository,
                uuid=request.args.get("uuid"),
                start=request.args.get("start", 0, type=int),
                limit=request.args.get("limit", None, type=int),
                json=True
            )
        else:
            return self.history(owner, repository)

    def r_api_repo_unit_history(self, owner, repository):
        """ Return json representation of one unit test

        :param owner: Name of the user
        :param repository: Name of the repository
        """
        return self.repo_report_unit(
            owner,
            repository,
            uuid=request.args.get("uuid"),
            unit=request.args.get("unit", "all")

        )

    @staticmethod
    def f_nice_ref(branch, commit):
        """ Transform a git formatted reference into something more human readable or returns part of commit sha

        :param branch: Github Reference
        :param commit: Commit SHA
        :return: Human readable reference
        """
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
        return HookUI.slugify(string)

    @staticmethod
    def f_checked_bool(boolean):
        """ Check a checkbox if boolean is true

        :param boolean: Boolean
        :return: "checked" if boolean is True
        """
        if boolean:
            return " checked "
        return ""

    @staticmethod
    def f_btn_bool(boolean):
        """ Return btn bs3 class depending on status

        :param boolean: Boolean
        :return: "btn-success" and "btn-danger" depending on boolean
        """
        if boolean:
            return "btn-success"
        return "btn-danger"

    @staticmethod
    def f_format_log(string):
        """ Format log string output from HookTest

        :param string: Log
        :return: Formatted log
        """
        if not string:
            return ""
        else:
            if string.startswith(">>> "):
                string = Markup("<u>{0}</u>".format(string.strip(">>> ")))
            elif string.startswith(">>>> "):
                string = Markup("<b>{0}</b>".format(string.strip(">>>> ")))
            elif string.startswith(">>>>> "):
                string = Markup("<i>{0}</i>".format(string.strip(">>>>> ")))
            elif HookUI.VERBOSE.findall(string):
                string = Markup("</li><li>".join(["<span class='verbose'>{0}</span>".format(found.strip(">>>>>> ")) for found in HookUI.VERBOSE.findall()]))
            elif string.startswith("[success]"):
                string = Markup("<span class='success'>{0}</span>".format(string.strip("[success]")))
            elif string.startswith("[failure]"):
                string = Markup("<span class='failure'>{0}</span>".format(string.strip("[failure]")))
            return string

    @staticmethod
    def f_check_tei(string):
        """ Check if value is "tei"

        :param string: String to check against "tei"
        :return: Checked class
        """
        if string == "tei":
            return "checked"
        return ""

    @staticmethod
    def f_check_epidoc(string):
        """ Check if value is "epidoc"

        :param string: String to check against "epidoc"
        :return: Checked class
        """
        if string == "epidoc":
            return "checked"
        return ""

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

    @staticmethod
    def slugify(value):
        """ Slugify a string

        :param value: String to HookUI.slugify
        :return: Slug
        """
        return slugify_library.slugify(value, only_ascii=True)
