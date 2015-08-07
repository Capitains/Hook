import threading
import subprocess
from uuid import uuid4
import collections
import git
import json
import re


from flask import abort, jsonify, request


from utils import Progress
from app import app
from models.logs import *

background_status = {}
background_logs = {}
background_git = {}
background_proc = {}
background_inf = {}

SCRIPT_PATH = "/home/thibault/dev/capitains/Hook/test/"
TEST_PATH = "/home/thibault/hooks"

int_finder = re.compile("([0-9]+)")

def test_repo(uuid, repository, branch):
    target = TEST_PATH + "/" + str(uuid)
    #
    # Taking care of cloning :
    #  
    background_git[uuid] = Progress()
    git.repo.base.Repo.clone_from(
        "https://github.com/{0}.git".format(repository),
        target, 
        progress=background_git[uuid]
    )
    # When cloning is finished, add repository cloned !
    background_git[uuid].update(0, background_git[uuid].current, background_git[uuid].maximum, "Repository cloned")

    #
    # Run the tests
    #
    background_logs[uuid] = []

    background_proc[uuid] = subprocess.Popen(
        ["/usr/bin/python3", SCRIPT_PATH + "__init__.py", "-n", uuid, repository, branch, TEST_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )

    lines_iterator = iter(background_proc[uuid].stdout.readline, b"")

    for line in lines_iterator:
        background_logs[uuid].append(line)

    lines_iterator = iter(background_proc[uuid].stderr.readline, b"")
    for line in lines_iterator:
        background_logs[uuid].append(line)

    #
    # It's finished !
    #
    background_status[uuid] = background_proc[uuid].wait()
    

def routined_save(uuid, repository, branch):
    username, reponame = tuple(repository.split("/"))
    logs, report, inf, status = logs_and_report(username, reponame, branch, uuid)
    if report is None:
        threading.Timer(10, lambda: routined_save(uuid, repository, branch)).start()
    return True

def launch(uuid, username, reponame, branch):
    t = threading.Thread(target=lambda: test_repo(uuid, username + "/" + reponame, branch))
    t.start()
    routined_save(uuid, username + "/" + reponame, branch)


@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/test')
def generate(username, reponame, branch):
    uuid = str(uuid4())
    background_status[uuid] = False
    launch(uuid, username, reponame, branch)

    #Create history
    repo = Repo_Get_Or_Create(uuid, username, reponame, branch)
    repo.save()

    return jsonify(
        id=uuid,
        repository=reponame,
        username=username,
        branch=branch,
        status="http://localhost:5000/api/rest/v1.0/code/{0}/{1}/{2}/test/{3}".format(username, reponame, branch, uuid)
    )

# For github :
#@app.route('/api/payload')
#
def logs_and_report(username, reponame, branch, uuid):
    if uuid in background_logs:
        logs = [line.decode("utf-8") for line in background_logs[uuid]]
    else:
        logs = []

    nb_files = 0
    tested = 0

    for el in logs:
        if el.startswith("files="):
            nb_files = int(int_finder.findall(el)[0])
            del logs[logs.index(el)]
        elif el == "test+=1\n":
            tested += 1
            del logs[logs.index(el)]

    background_inf[uuid] = { "files" : nb_files, "tested": tested}

    # Update the record
    repo = Repo_Get_Or_Create(uuid, username, reponame, branch)
    repo.total = nb_files
    repo.tested = tested
    repo.save()

    if "====JSON====\n" in logs:
        json_index = logs.index("====JSON====\n")
        if len(logs) >= json_index + 2: # 2 Because index are 0 based and we need json header line and the following line
            report = json.loads(logs[json_index+1])
            logs = logs[:json_index]
        else:
            report = None
    else:
        report = None

    logs = [line for line in background_git[uuid].json()] + [line for line in logs if line != "\n" and line]

    answer = (logs, report, background_inf[uuid], background_status[uuid])

    if report is not None:
        save_logs(report, logs, username, reponame, branch, uuid)
        del background_git[uuid]
        del background_status[uuid]
        del background_logs[uuid]
        del background_proc[uuid]
        del background_inf[uuid]

    return answer

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/test/<uuid>')
def status(username, reponame, branch, uuid):
    if uuid not in background_status:
        return db_status(username, reponame, branch, uuid)

    logs, report, inf, status = logs_and_report(username, reponame, branch, uuid)

    return jsonify(
        progress=inf,
        logs=logs,
        report=report,
        done=status
    )


def db_status(username, reponame, branch, uuid):
    """ Return the logs and status when the test is finished """
    repo_test = RepoTest.objects.get_or_404(username=username, reponame=reponame, branch=branch, uuid=uuid)

    units = {}
    for document in repo_test.units:
        units[document.path] = {
            "status" : document.status,
            "coverage" : document.coverage,
            "units" : {doc_test.title:doc_test.status for doc_test in document.logs}
        }

    answer = jsonify(

        progress = { "files" : repo_test.total, "tested": repo_test.tested},
        logs=[log.text for log in repo_test.logs],
        report={
            "coverage" : repo_test.coverage,
            "status"   : repo_test.status,
            "units" : units
        },
        done=int(repo_test.status)
    )
    return answer

def Repo_Get_Or_Create(uuid, username, reponame, branch):
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
    else:
        repo_test = repo_test.first()
    return repo_test

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
    repo_test = Repo_Get_Or_Create(
        uuid=uuid,
        username=username,
        reponame=reponame,
        branch=branch
    )

    # Save direct informations
    repo_test.branch=branch
    repo_test.status=report["status"]
    repo_test.coverage=report["coverage"]

    # Save the full logs
    for line in logs:
        repo_test.logs.append(RepoLogs(text=line))

    for document_name, document_test in report["units"].items():
        document_mongo = DocTest(
            path=document_name,
            status=document_test["status"],
            coverage=document_test["coverage"]
        )

        for test_name, test_status in document_test["units"].items():
            document_mongo.logs.append(DocLogs(
                title=test_name,
                status=test_status
            ))

        repo_test.units.append(document_mongo)

    repo_test.save()