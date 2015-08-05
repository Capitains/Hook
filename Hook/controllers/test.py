import threading
import subprocess
import uuid
import collections
import git
import json


from flask import abort, jsonify, request


from utils import Progress
from app import app
from models.logs import *

background_status = {}
background_logs = {}
background_git = {}
background_proc = {}

SCRIPT_PATH = "/home/thibault/dev/capitains/Hook/test/"
TEST_PATH = "/home/thibault/hooks"

def test_repo(id, repository, branch):
    target = TEST_PATH + "/" + str(id)
    #
    # Taking care of cloning :
    #  
    background_git[id] = Progress()
    git.repo.base.Repo.clone_from(
        "https://github.com/{0}.git".format(repository),
        target, 
        progress=background_git[id]
    )
    # When cloning is finished, add repository cloned !
    background_git[id].update(0, background_git[id].current, background_git[id].maximum, "Repository cloned")

    #
    # Run the tests
    #
    background_logs[id] = []

    background_proc[id] = subprocess.Popen(
        ["/usr/bin/python3", SCRIPT_PATH + "__init__.py", "-v", id, repository, branch, TEST_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )

    lines_iterator = iter(background_proc[id].stdout.readline, b"")
    for line in lines_iterator:
        background_logs[id].append(line)

    lines_iterator = iter(background_proc[id].stderr.readline, b"")
    for line in lines_iterator:
        background_logs[id].append(line)

    #
    # It's finished !
    #
    background_status[id] = background_proc[id].wait()

def launch(id, username, reponame, branch):
    t = threading.Thread(target=lambda: test_repo(id, username + "/" + reponame, branch))
    t.start()


@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/test')
def generate(username, reponame, branch):
    id = str(uuid.uuid4())
    background_status[id] = False
    launch(id, username, reponame, branch)

    return jsonify(
        id=id,
        repository=reponame,
        username=username,
        branch=branch,
        status="http://localhost/api/rest/v1.0/code/{0}/{1}/{2}/test/{3}".format(username, reponame, branch, id)
    )

# For github :
#@app.route('/api/payload')

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/test/<id>')
def status(username, reponame, branch, id):
    if id not in background_status:
        return db_status(username, reponame, branch, id)

    if id in background_logs:
        logs = [line.decode("utf-8") for line in background_logs[id]]
    else:
        logs = ""

    if "====JSON====\n" in logs:
        report = json.loads(logs[-1])
        logs = logs[:-2]
    else:
        report = None

    if report is not None:
        threading.Thread(target=lambda: save_logs(report, [line for line in background_git[id].json()] + [line for line in logs if line != "\n" and line], username, reponame, branch, id)).start()

    answer = jsonify(
        logs=background_git[id].json() + logs,
        report=report,
        done=background_status[id]
    )
    if report is not None:
        del background_git[id]
        del background_status[id]
        del background_logs[id]
        del background_proc[id]

    return answer


def db_status(username, reponame, branch, uuid):
    repo_test = RepoTest.objects.get_or_404(username=username, reponame=reponame, branch=branch, uuid=uuid)

    units = {}
    for document in repo_test.units:
        units[document.path] = {
            "status" : document.status,
            "coverage" : document.coverage,
            "units" : {doc_test.title:doc_test.status for doc_test in document.logs}
        }

    answer = jsonify(
        logs=[log.text for log in repo_test.logs],
        report={
            "coverage" : repo_test.coverage,
            "status"   : repo_test.status,
            "units" : units
        },
        done=int(repo_test.status)
    )
    return answer

def save_logs(report, logs, username, reponame, branch, uuid):
    """ Save logs to MongoDB

    :param report: Dictionary of logs issued by test script
    :type report: dict
    :param logs: Textual logs
    :type logs: list
    :param username: Username of the repo's owner
    :type username: str
    :param reponame: Repository's name
    :type reponame: str
    :param branch: Branch's name
    :type branch: str
    :param uuid: Id representing the test
    :type uuid: str

    """

    repo_test = RepoTest(
        uuid=uuid,
        username=username,
        reponame=reponame,
        userrepo=username+"/"+reponame,
        branch=branch,
        status=report["status"],
        coverage=report["coverage"]
    )

    # Save the full logs
    for line in logs:
        repo_test.logs.append(RepoLogs(text=line))

    for document_name, document_test in report["units"].items():
        document_mongo = DocTest(
            path=document_name,
            status=report["status"],
            coverage=report["coverage"]
        )

        for test_name, test_status in document_test["units"].items():
            document_mongo.logs.append(DocLogs(
                title=test_name,
                status=test_status
            ))

        repo_test.units.append(document_mongo)

    repo_test.save()