"""
    This controller covers the testing functionnalities, including saving tests results and formatting them
"""
# Multiprocessing related libraries
import threading
import subprocess

# Test related informations
from uuid import uuid4
import git
import shutil

# General use libraries
import json
import re

# Flask imports
from flask import g, jsonify, Response

# Database imports
from Hook.utils import Progress
from Hook.app import app, github_api
import Hook.models.user
import Hook.models.logs

"""
    Dictionaries for status checking
"""
background_status = {}
background_logs = {}
background_git = {}
background_proc = {}
background_inf = {}
background_timer = {}
background_main = {}

SCRIPT_PATH = app.config["SCRIPT_PATH"]
TEST_PATH = app.config["TEST_PATH"]

int_finder = re.compile("([0-9]+)")
pr_finder = re.compile("PR #([0-9]+)")
rng = re.compile("([0-9]+):([0-9]+):(.*);")
rng_fatal = re.compile("([0-9]+):([0-9]+):(\s*fatal.*)")
def remove(uuid):
    """ Remove uuid object from current procs and Remove the cloned folder of the uuid identified repo

    :param uuid:
    :type uuid:
    """
    if uuid in background_status:
        del background_status[uuid]

    if uuid in background_logs:
        del background_logs[uuid]

    if uuid in background_main:
        # Need to find a way to kill if necessary
        #background_main[uuid].kill()
        del background_main[uuid]

    if uuid in background_git:
        del background_git[uuid]

    if uuid in background_proc:
        background_proc[uuid].kill()
        del background_proc[uuid]

    if uuid in background_inf:
        del background_inf[uuid]

    if uuid in background_timer:
        background_timer[uuid].kill()
        del background_timer[uuid]

    shutil.rmtree(TEST_PATH + "/" + str(uuid), ignore_errors=True)

def test(uuid, repository, branch, db_obj):
    """ Download, clone and launch the test

    :param uuid: Unique identifier for the current test
    :type uuid: str
    :param repository: Repository to be tested
    :type repository: str
    :param branch: branch to be tested
    :type branch: str
    :param db_obj: Repo instance of the database
    :type db_obj: Hook.models.logs.RepoTest

    """
    target = TEST_PATH + "/" + str(uuid)

    db_obj.git_status()

    #
    # Taking care of cloning :
    #  
    background_git[uuid] = Progress()

    repo = git.repo.base.Repo.clone_from(
        url="https://github.com/{0}.git".format(repository),
        to_path=target,
        progress=background_git[uuid]
    )

    if pr_finder.match(branch):
        branch = pr_finder.findall(branch)[0]
        ref = "refs/pull/{0}/head:refs/pull/origin/{0}".format(branch)
    else:
        ref = "refs/heads/{ref}".format(ref=branch)

    repo.remote().pull(ref, progress=background_git[uuid])

    # When cloning is finished, add repository cloned !
    background_git[uuid].update(0, background_git[uuid].current, background_git[uuid].maximum, "Repository cloned")

    #
    # Run the tests
    #
    background_logs[uuid] = []

    background_proc[uuid] = subprocess.Popen(
        ["/usr/bin/python3", SCRIPT_PATH + "test.py", "-"+"".join(db_obj.config_to()), uuid, repository, branch, TEST_PATH],
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
        background_timer[uuid] = threading.Timer(10, lambda: watch(uuid, repository, branch)).start()
    return True

def format_log(log):
    found = rng.findall(log)
    if len(found) > 0:
        log = ">>>>>> DTD l{0} c{1} : {2}".format(*found[0])
    else:
        found = rng_fatal.findall(log)
        if len(found) > 0:
            log = ">>>>>> DTD l{0} c{1} : {2}".format(*found[0])
    return log

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

    logs = [format_log(line) for line in logs if line != "\n" and line]

    if uuid in background_git:
        logs = [line for line in background_git[uuid].json()] + logs

    answer = (logs, report, background_inf[uuid], background_status[uuid])

    repository = update(report, logs, username, reponame, branch, uuid, nb_files, tested)

    if report is not None:
        # Update the status on github
        repository.git_status()
        try:
            remove(uuid)
        except Exception as E:
            print(E)

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
    repo_test = Hook.models.logs.RepoTest.Get_or_Create(
        uuid=uuid,
        username=username,
        reponame=reponame,
        branch=branch
    )

    repo_test.total = nb_files
    repo_test.tested = tested
    repo_test.branch = branch

    # Save the full logs
    for line in logs:
        repo_test.logs.append(Hook.models.logs.RepoLogs(text=line))

    if report is not None:

        # Save direct informations
        repo_test.status=report["status"]
        repo_test.coverage=report["coverage"]

        for document_name, document_test in report["units"].items():
            document_mongo = Hook.models.logs.DocTest(
                path=document_name,
                status=document_test["status"],
                coverage=document_test["coverage"]
            )

            for test_name, test_status in document_test["units"].items():
                document_mongo.logs.append(Hook.models.logs.DocLogs(
                    title=test_name,
                    status=test_status
                ))

            repo_test.units.append(document_mongo)

    repo_test.save()
    return repo_test

def launch(username, reponame, ref, creator, gravatar, sha):
    """ Launch test into multithread.

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param ref: branch to be tested
    :type ref: str

    :returns: Identifier of the test
    :rtype: str
    """

    if isinstance(ref, int):
        ref = "PR #{0}".format(ref)
    elif "/" in ref:
        ref = ref.split("/")[-1]

    uuid = str(uuid4())
    background_status[uuid] = False

    repo = Hook.models.logs.RepoTest.Get_or_Create(uuid, username, reponame, ref)
    repo.user = creator
    repo.gravatar = gravatar
    repo.sha = sha
    repo.save()

    background_main[uuid] = threading.Thread(target=lambda: test(uuid, username + "/" + reponame, ref, repo))
    background_main[uuid].start()
    watch(uuid, username + "/" + reponame, ref)

    return uuid, repo.branch_slug


def api_test_generate(username, reponame, branch=None, creator=None, gravatar=None, sha=None, github=False):
    """ Generate a test on the machine

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    .:warning:. DISABLED
    """
    # Need to ensure the repository exists
    
    if github is not True:
        repository = Hook.models.user.Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame, authors__in=[g.user])
    else:
        repository = Hook.models.user.Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)

    # Fill data when required
    if branch is None and hasattr(g, "user") and g.user is not None:
        status = github_api.get(
            "repos/{owner}/{name}/commits".format(owner=repository.owner, name=repository.name),
            params = {"sha" : "master"}
        )
        if len(status) == 0:
            return Response(
                response=json.dumps({"error" : "No commits available"}),
                headers={"Content-Type": "application/json"},
                status="404"
            )

        sha = status[0]["sha"]
        branch = "master"
        creator = g.user.login
        gravatar = "https://avatars.githubusercontent.com/{0}".format(creator)

    # Check that no test are made on the same
    running = Hook.models.logs.RepoTest.objects(username__iexact=username, reponame__iexact=reponame, sha=sha, branch=branch, status=None)
    if len(running) > 0:
        return Response(
            response=json.dumps({"error" : "Test already running on this branch"}),
            headers={"Content-Type": "application/json"},
            status="404"
        )
    elif not Hook.models.logs.RepoTest.is_ok(username=username, reponame=reponame, branch=branch):
        return Response(
            response=json.dumps({"error" : "This branch is not taken into account by our configuration"}),
            headers={"Content-Type": "application/json"},
            status="404"
        )

    uuid, slug = launch(repository.owner, repository.name, branch, creator, gravatar, sha)

    return jsonify(
        uuid=uuid,
        owner=repository.owner,
        name=repository.name,
        branch=branch,
        status="/api/rest/v1.0/code/{0}/{1}/{2}/test/{3}".format(repository.owner, repository.name, slug, uuid)
    )