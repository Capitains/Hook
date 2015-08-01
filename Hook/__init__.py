import threading
import subprocess
import uuid
from flask import Flask
from flask import render_template, url_for, abort, jsonify, request
import tempfile
import collections

import git
from utils import Progress

app = Flask(__name__, template_folder="../data/templates")

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
        ["python", SCRIPT_PATH + "cts.py", id, repository, branch, TEST_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )

    lines_iterator = iter(background_proc[id].stdout.readline, b"")
    for line in lines_iterator:
        background_logs[id].append(line)

    #
    # It's finished !
    #
    background_status[id] = background_proc[id].wait()

def launch(id, username, reponame, branch):
    t = threading.Thread(target=lambda: test_repo(id, username + "/" + reponame, branch))
    t.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test/<username>/<reponame>/<branch>')
def generate(username, reponame, branch):
    id = str(uuid.uuid4())
    background_status[id] = False
    launch(id, username, reponame, branch)
    return render_template('processing.html', id=id)

@app.route('/status/<id>')
def status(id):
    if id not in background_status:
        abort(404)

    if id in background_logs:
        print(background_logs)
        test = "".join([line.decode("utf-8") for line in background_logs[id]])
    else:
        test = ""

    return jsonify(
        git =background_git[id].json(),
        test=test,
        done=background_status[id]
    )

if __name__ == '__main__':
    app.debug = True
    app.run()