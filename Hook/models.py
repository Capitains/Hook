import datetime
import re

from flask import g
from Hook.extensions import db
from Hook.utils import slugify

__author__ = 'Thibault Clerice'


pr_finder = re.compile("PR #([0-9]+)")


class User(db.Document):
    """ User information """
    uuid  = db.StringField(max_length=200, required=True)
    mail = db.StringField(required=False)
    login = db.StringField(required=True)
    git_id = db.IntField(required=True)
    github_access_token = db.StringField(max_length=200, required=True)
    refreshed = db.DateTimeField(default=datetime.datetime.now, required=True)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.uuid == self.uuid

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    def get_id(self):
        return self.uuid

    def remove_authorship(self):
        """ Remove list of repositories """
        for repo in self.repositories:
            repo.update(pull__authors=self)

    @property
    def repositories(self):
        return list(Repository.objects(authors__in=[self]))

    @property
    def organizations(self):
        return Repository.objects(authors__in=[self]).distinct("owner")

    @property
    def testable(self):
        return Repository.objects(authors__in=[self], tested=True)

    def switch(self, owner, name, callback):
        return Repository.switch(owner, name, self, callback)

    def repository(self, owner, name):
        return Repository.objects(authors__in=[self], owner__iexact=owner, name__iexact=name)

    def addto(self, owner, name):
        """ Add the user to the authors of a repository. Create
            Create the repository if required

        :param owner: Owner name of the repository
        :type owner: str
        :param name: Name of the repository
        :type name: str

        :return: New or Updated repository
        :rtype: Repository
        """
        repo_db = self.repository(owner=owner, name=name)

        if len(repo_db) > 0:
            repo_db = repo_db.first()
            repo_db.update(push__authors=self)
        else:
            repo_db = Repository(owner=owner, name=name, authors=[self])
            repo_db.save()

        return repo_db


class Repository(db.Document):
    """ Just as a cache of available repositories for user """
    owner = db.StringField(max_length=200, required=True)
    name = db.StringField(max_length=200, required=True)
    tested = db.BooleanField(default=False)
    hook_id = db.IntField(default=None)
    dtd = db.StringField(default="tei", max_length=3)
    master_pr = db.BooleanField(default=False)
    verbose = db.BooleanField(default=False)
    authors = db.ListField(db.ReferenceField(User))

    @property
    def full_name(self):
        return self.owner + "/" + self.name

    def dict(self):
        return {
            "owner": self.owner,
            "name": self.name
        }

    def isWritable(self, user):
        if user in self.authors:
            return True
        return False

    def config(self, form):
        """ Update the object config """
        dtd, master_pr, verbose = self.dtd, False, False
        if "dtd" in form:
            if form["dtd"] in ["tei", "epidoc"]:
                dtd = form["dtd"]
        if "masterpr" in form:
            master_pr = True
        if "verbose" in form:
            verbose = True

        self.update(dtd=dtd, master_pr=master_pr, verbose=verbose)
        self.reload()
        self.updated = True

    @staticmethod
    def switch(owner, name, user, callback=lambda x: True):
        """ Switch a given repository for automatic PR/Push builds

        :param owner: Name of the repository's owner
        :type owner: str
        :param name: Name of the repository
        :type name: str
        :param user: User author of the repository
        :type user: user.User
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


class DocUnitStatus(db.EmbeddedDocument):
    """ Unittest level logs """
    title = db.StringField(max_length=255, required=True)
    status = db.BooleanField(required=False)


class DocLogs(db.EmbeddedDocument):
    """ Verbose result for unit test """
    text = db.StringField(required=True)


class DocTest(db.EmbeddedDocument):
    """ Complete Document level status"""
    at = db.DateTimeField(default=datetime.datetime.now, required=True)
    path = db.StringField(required=True)
    status = db.BooleanField(required=True)
    coverage = db.FloatField(min_value=0.0, max_value=100.0, required=True)
    logs = db.EmbeddedDocumentListField(DocUnitStatus)
    text_logs = db.EmbeddedDocumentListField(DocLogs)

    meta = {
        'ordering': ['at']
    }


class RepoTest(db.Document):
    """ Complete repository status """
    # Running informations
    POSSIBLE_STATUS = ["queued", "downloading", "pending", "failed", "error", "success"]
    run_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    uuid = db.StringField(required=True)
    hash = db.StringField()

    # Inventory not moving information
    repository = db.ReferenceField(Repository)
    branch = db.StringField(default=None)
    branch_slug = db.StringField(required=True)

    # Test results
    status = db.StringField(default="queued")
    error_message = db.StringField(default=None)
    # inqueue, downloading, pending, failed, error, success
    coverage = db.FloatField(min_value=0.0, max_value=100.0, default=None)
    cts_metadata = db.IntField(default=0)
    texts = db.IntField(default=0)
    units = db.EmbeddedDocumentListField(DocTest)

    # Commit related informations
    user = db.StringField(default="")
    gravatar = db.StringField(default="")
    sha = db.StringField(default="")
    link = db.StringField()

    # Test Configuration
    scheme = db.StringField(default="tei")
    verbose = db.BooleanField(default=False)

    meta = {
        'ordering': ['-run_at']
    }

    @property
    def tested(self):
        return len(self.units)

    @property
    def total(self):
        return self.texts + self.cts_metadata

    @property
    def finished(self):
        return self.status in ["failed", "error", "success"]

    def ctsized(self):
        """ Get information about CTSized texts

        :return: Total number of ctsized texts, total number of texts
        :rtype: (int, int)
        """
        units = [unit.status for unit in  self.units if "__cts__.xml" not in unit.path]
        return units.count(True), len(units)

    @staticmethod
    def report(repository, slug=None, uuid=None, repo_test=None):
        """ Return the logs and status when the test is finished

        :param repository: Repository for which the test has been performed
        :type repository: Repository
        :param slug: branch to be tested
        :type slug: str
        :param uuid: Unique identifier for the current test
        :type uuid: str
        :param repo_test: RepoTest object for which to find the report
        :type repo_test: RepoTest

        :returns: Logs, Detailed report, Current progress, Overall status
        :rtype: list, dict, dict, int
        """
        if repo_test is None:
            repo_test = RepoTest.objects.get_or_404(repository=repository, branch_slug__iexact=slug, uuid=uuid)

        units = {}


        for document in repo_test.units:
            units[document.path] = {
                "status": document.status,
                "coverage": document.coverage,
                "units": {doc_test.title:doc_test.status for doc_test in document.logs}
            }

        answer = {
            "progress": {"files": repo_test.total, "tested": repo_test.tested},
            "logs": [log.text for unit in repo_test.units for log in unit.text_logs],
            "report": {
                "coverage": repo_test.coverage,
                "status": repo_test.status,
                "units": units
            },
            "status": repo_test.status,
            "error" : repo_test.error_message
        }

        return answer

    @staticmethod
    def Get_or_Create(uuid, repository, branch=None, slug=None, **kwargs):
        """ Find said RepoTest is not found, create an instance for it

        :param repository: Repository for which the test has been performed
        :type repository: Repository
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
                repository=repository,
                branch_slug__iexact=slug
            )
        else:
            slug = slugify(branch)
            repo_test = RepoTest.objects(
                uuid__iexact=uuid,
                repository=repository,
                branch__iexact=branch,
                branch_slug=slug
            )
        if len(repo_test) == 0:
            repo_test = RepoTest(
                uuid=uuid,
                repository=repository,
                branch=branch,
                branch_slug=slug,
                scheme=repository.dtd,
                verbose=repository.verbose,
                **kwargs
            )
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