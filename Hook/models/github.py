import datetime
import re
from flask import g
from Hook.extensions import db
from Hook.utils import slugify

import Hook.extensions
import Hook.models.user
import Hook.controllers.github

__author__ = 'Thibault Clerice'


pr_finder = re.compile("PR #([0-9]+)")


class Repository(db.Document):
    """ Just as a cache of available repositories for user """
    owner = db.StringField(max_length=200, required=True)
    name = db.StringField(max_length=200, required=True)
    tested = db.BooleanField(default=False)
    hook_id = db.IntField(default=None)
    dtd = db.StringField(default="t", max_length=1)
    master_pr = db.BooleanField(default=False)
    verbose = db.BooleanField(default=False)
    authors = db.ListField(db.ReferenceField(Hook.models.user.User))

    def dict(self):
        return {
            "owner": self.owner,
            "name": self.name
        }

    def isWritable(self):
        if g.user and g.user in self.authors:
            return True
        return False

    def config(self, form):
        """ Update the object config """
        dtd, master_pr, verbose = self.dtd, False, False
        if "dtd" in form:
            if form["dtd"] in ["t", "e"]:
                dtd = form["dtd"]
        if "masterpr" in form:
            master_pr = True
        if "verbose" in form:
            verbose = True

        self.update(dtd=dtd, master_pr=master_pr, verbose=verbose)
        self.reload()
        self.updated = True

    @staticmethod
    def switch(owner, name, user, callback=Hook.controllers.github.hook):
        """ Switch a given repository for automatic PR/Push builds

        :param owner: Name of the repository's owner
        :type owner: str
        :param name: Name of the repository
        :type name: str
        :param user: User author of the repository
        :type user: Hook.models.user.User
        :param callback: Function to call when DB switch has been done
        :type callback: function

        :return: Callback response
        """
        repository = Repository.objects(authors__in=[user], owner__iexact=owner, name__iexact=name)
        if len(repository) > 0:
            repository = repository.first()
            tested = not repository.tested
            repository.update(tested=tested)
            repository.reload()
            return callback(repository)
        return None


class DocLogs(db.EmbeddedDocument):
    """ Unittest level logs """
    title = db.StringField(max_length=255, required=True)
    status = db.BooleanField(required=False)


class DocTest(db.EmbeddedDocument):
    """ Complete Document level status"""
    path = db.StringField(required=True)
    status = db.BooleanField(required=True)
    coverage = db.FloatField(min_value=0.0, max_value=100.0, required=True)
    logs = db.EmbeddedDocumentListField(DocLogs)


class RepoLogs(db.EmbeddedDocument):
    text = db.StringField(required=True)


class RepoTest(db.Document):
    """ Complete repository status """
    run_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    uuid = db.StringField(required=True)
    username = db.StringField(required=True)
    reponame = db.StringField(required=True)
    userrepo = db.StringField(required=True)
    branch = db.StringField(default=None)
    branch_slug = db.StringField(required=True)
    status = db.BooleanField(default=None)
    coverage = db.FloatField(min_value=0.0, max_value=100.0, default=None)
    logs = db.EmbeddedDocumentListField(RepoLogs)
    units = db.EmbeddedDocumentListField(DocTest)
    total = db.IntField(default=1)
    tested = db.IntField(default=0)
    config = db.ListField(db.StringField())
    repository = db.ReferenceField(Repository())

    user = db.StringField(default="")
    gravatar = db.StringField(default="")
    sha = db.StringField(default="")

    DTDS_KEYS = {"tei": "t", "epidoc": "e", "verbose": "v"}
    meta = {
        'ordering': ['-run_at']
    }

    def ctsized(self):
        """ Get information about CTSized texts

        :return: Total number of ctsized texts, total number of texts
        :rtype: (int, int)
        """
        units = [unit.status for unit in  self.units if "__cts__.xml" not in unit.path]
        return units.count(True), len(units)

    def config_to(self):
        return [RepoTest.DTDS_KEYS[key] for key in self.config if key in dtds]

    @staticmethod
    def report(username, reponame, slug=None, uuid=None, repo_test=None):
        """ Return the logs and status when the test is finished


        :param username: Name of the user
        :type username: str
        :param reponame: Name of the repository
        :type reponame: str
        :param slug: branch to be tested
        :type slug: str
        :param uuid: Unique identifier for the current test
        :type uuid: str

        :returns: Logs, Detailed report, Current progress, Overall status
        :rtype: list, dict, dict, int
        """
        if repo_test is None:
            repo_test = RepoTest.objects.get_or_404(username=username, reponame=reponame, branch_slug__iexact=slug, uuid=uuid)

        units = {}

        if repo_test.status is None:
            done = None
        else:
            done = int(repo_test.status)

        for document in repo_test.units:
            units[document.path] = {
                "status": document.status,
                "coverage": document.coverage,
                "units": {doc_test.title:doc_test.status for doc_test in document.logs}
            }

        answer = {
            "progress": {"files": repo_test.total, "tested": repo_test.tested},
            "logs": [log.text for log in repo_test.logs],
            "report": {
                "coverage": repo_test.coverage,
                "status": repo_test.status,
                "units": units
            },
            "done": done
        }

        return answer

    @staticmethod
    def Get_or_Create(uuid, username, reponame, branch=None, slug=None, save=False):
        """ Find said RepoTest is not found, create an instance for it

        :param username: Username of the repo's owner
        :type username: str
        :param reponame: Repository's name
        :type reponame: str
        :param branch: Branch's name
        :type branch: str
        :param uuid: Id representing the test
        :type uuid: str
        :param save: If set to True, if the object does not exist, save it
        :type save: boolean

        :returns: A Repository logs
        :rtype: RepoTest

        """

        if slug is not None:
            repo_test = RepoTest.objects(
                uuid__iexact=uuid,
                username__iexact=username,
                reponame__iexact=reponame,
                branch_slug__iexact=slug,
                userrepo__iexact=username+"/"+reponame
            )
        else:
            slug = slugify(branch)
            repo_test = RepoTest.objects(
                uuid__iexact=uuid,
                username__iexact=username,
                reponame__iexact=reponame,
                branch__iexact=branch,
                userrepo__iexact=username+"/"+reponame,
                branch_slug=slug
            )
        if len(repo_test) == 0:
            repository = Repository.objects.get(owner__iexact=username, name__iexact=reponame)
            repo_test = RepoTest(
                uuid=uuid,
                username=username,
                reponame=reponame,
                branch=branch,
                userrepo=username+"/"+reponame,
                branch_slug=slug,
                config=RepoTest.config_from(repository)
            )
            if save is True:
                repo_test.save()
        else:
            repo_test = repo_test.first()
        return repo_test

    @staticmethod
    def is_ok(username, reponame, branch):
        """ Check that the test is accepted by config

        :param username: Username of the repo's owner
        :type username: str
        :param reponame: Repository's name
        :type reponame: str
        :param branch: Branch's name
        :type branch: str

        :returns: Acceptance
        :rtype: Boolean
        """
        repository = Repository.objects.get(owner__iexact=username, name__iexact=reponame)
        if repository.master_pr and \
          branch is not None and \
          isinstance(branch, str) and \
          "master" not in branch and \
          pr_finder.match(branch) is None:
            return False

        return True

    @staticmethod
    def config_from(repository):
        """ Make a RepoTest config from a Repository object

        :param repository: Repository object to read the configuration from
        :type repository: RepoTest
        :returns: List of options
        :rtype: list
        """
        config = []
        dtds = {"t": "tei", "e": "epidoc"}
        config.append(dtds[repository.dtd])

        if repository.verbose:
            config.append("verbose")

        return config
