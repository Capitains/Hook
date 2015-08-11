import datetime
from app import db


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
    status = db.BooleanField(default=None)
    coverage = db.FloatField(min_value=0.0, max_value=100.0, default=None)
    logs = db.EmbeddedDocumentListField(RepoLogs)
    units = db.EmbeddedDocumentListField(DocTest)
    total = db.IntField(default=1)
    tested = db.IntField(default=0)
    
    meta = {
        'ordering': ['-run_at']
    }

    def Get_or_Create(uuid, username, reponame, branch, save=False):
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
        repo_test = RepoTest.objects(
            uuid__iexact=uuid,
            username__iexact=username,
            reponame__iexact=reponame,
            branch__iexact=branch,
            userrepo__iexact=username+"/"+reponame
        )
        if len(repo_test) == 0:
            repo_test = RepoTest(
                uuid=uuid,
                username=username,
                reponame=reponame,
                branch=branch,
                userrepo=username+"/"+reponame
            )
            if save is True:
                repo_test.save()
        else:
            repo_test = repo_test.first()
        return repo_test

    def report(username, reponame, branch, uuid):
        """ Return the logs and status when the test is finished 


        :param username: Name of the user
        :type username: str
        :param reponame: Name of the repository
        :type reponame: str
        :param branch: branch to be tested
        :type branch: str
        :param uuid: Unique identifier for the current test
        :type uuid: str

        :returns: Logs, Detailed report, Current progress, Overall status
        :rtype: list, dict, dict, int
        """
        repo_test = RepoTest.objects.get_or_404(username=username, reponame=reponame, branch=branch, uuid=uuid)

        units = {}
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
            "done" : int(repo_test.status)
        }

        return answer