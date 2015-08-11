"""
    This controller covers the testing functionnalities, including saving tests results and formatting them
"""
# Multiprocessing related libraries
import threading
import subprocess

# Test related informations
from uuid import uuid4
import git
from utils import Progress

# General use libraries
import json
import re

# Database imports
from models.logs import *

"""
    Dictionaries for status checking
"""
background_status = {}
background_logs = {}
background_git = {}
background_proc = {}
background_inf = {}

SCRIPT_PATH = "/home/thibault/dev/capitains/Hook/test/"
TEST_PATH = "/home/thibault/hooks"

int_finder = re.compile("([0-9]+)")

def test(uuid, repository, branch):
    """ Download, clone and launch the test

    :param uuid: Unique identifier for the current test
    :type uuid: str
    :param repository: Repository to be tested
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    """
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
    

def watch(uuid, repository, branch):
    """ Save routinely information about the selected repository

    :param uuid: Unique identifier for the current test
    :type uuid: str
    :param repository: Repository to be tested
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    :returns: True

    """
    username, reponame = tuple(repository.split("/"))
    logs, report, inf, status = read(username, reponame, branch, uuid)

    if report is None:
        threading.Timer(10, lambda: watch(uuid, repository, branch)).start()
    return True

def read(username, reponame, branch, uuid):
    """ Exploit logs informations 

    .:note:. This function is responsible for updating the status in the database as well as reading the logs

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

    update(report, logs, username, reponame, branch, uuid, nb_files, tested)

    if report is not None:
        del background_git[uuid]
        del background_status[uuid]
        del background_logs[uuid]
        del background_proc[uuid]
        del background_inf[uuid]

    return answer


def update(report, logs, username, reponame, branch, uuid, nb_files=1, tested=0):
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
    :param nb_files: Number of files to be tested
    :type nb_files: int
    :param tested: Number of files already tested
    :type tested: int

    """
    repo_test = RepoTest.Get_or_Create(
        uuid=uuid,
        username=username,
        reponame=reponame,
        branch=branch
    )

    repo_test.total = nb_files
    repo_test.tested = tested
    repo_test.branch = branch

    if report is not None:

        # Save direct informations
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

def launch(username, reponame, branch):
    """ Launch test into multithread.

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    :returns: Identifier of the test
    :rtype: str
    """

    uuid = str(uuid4())
    background_status[uuid] = False

    RepoTest.Get_or_Create(uuid, username, reponame, branch, save=True)

    t = threading.Thread(target=lambda: test(uuid, username + "/" + reponame, branch))
    t.start()
    watch(uuid, username + "/" + reponame, branch)

    return uuid