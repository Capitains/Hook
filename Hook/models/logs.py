import datetime
from utils import slugify
from flask import url_for, g


from app import db, github_api, app
from models.user import *



class DocLogs(db.EmbeddedDocument):
    """ Unittest level logs """
    title  = db.StringField(max_length=255, required=True)
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

    user = db.StringField(default="")
    gravatar = db.StringField(default="")
    sha = db.StringField(default="")
    
    meta = {
        'ordering': ['-run_at']
    }

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
            repo_test = RepoTest(
                uuid=uuid,
                username=username,
                reponame=reponame,
                branch=branch,
                userrepo=username+"/"+reponame,
                branch_slug=slug
            )
            if save is True:
                repo_test.save()
        else:
            repo_test = repo_test.first()
        return repo_test

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
            done=0
        else:
            done = int(repo_test.status)

        for document in repo_test.units:
            units[document.path] = {
                "status" : document.status,
                "coverage" : document.coverage,
                "units" : {doc_test.title:doc_test.status for doc_test in document.logs}
            }

        answer = {
            "progress" : { "files" : repo_test.total, "tested": repo_test.tested},
            "logs" : [log.text for log in repo_test.logs],
            "report" : {
                "coverage" : repo_test.coverage,
                "status"   : repo_test.status,
                "units" : units
            },
            "done" : done
        }

        return answer

    def git_status(self, state=None):

        with app.app_context():
            uri = "repos/{owner}/{repo}/statuses/{sha}".format(owner=self.username, repo=self.reponame, sha=self.sha)
            if state is not None:
                state = "error"
                sentence = "Test cancelled"
            elif self.status is True:
                state = "success"
                sentence = "Full repository is cts compliant"
            elif self.status is False:
                state = "failure"
                sentence = "{0} of unit tests passed".format(self.coverage)
            else:
                state = "pending"
                sentence = "Currently testing..."

            data = {
              "state": state,
              "target_url": app.config["DOMAIN"]+"/repo/{username}/{reponame}/{uuid}".format(username=self.username, reponame=self.reponame, uuid=self.uuid),
              "description": sentence,
              "context": "continuous-integration/capitains-hook"
            }

            params = {}
            if hasattr(g, "user") is not True:
                full_repository = Repository.objects.get(owner__iexact=self.username, name__iexact=self.reponame)
                user = full_repository.authors[0]
                access_token = user.github_access_token
                params = {"access_token" : access_token}

            print(github_api.post(uri, data=data, params=params))
        return True