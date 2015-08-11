from flask import abort, jsonify, request
from app import app

import controllers.test
import models.logs

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/test')
def generate(username, reponame, branch):
    """ Generate a test on the machine

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param branch: branch to be tested
    :type branch: str
    """
    uuid = controllers.test.launch(username, reponame, branch)

    return jsonify(
        id=uuid,
        repository=reponame,
        username=username,
        branch=branch,
        status="/api/rest/v1.0/code/{0}/{1}/{2}/test/{3}".format(username, reponame, branch, uuid)
    )

# For github :
#@app.route('/api/payload')
#

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/test/<uuid>')
def status(username, reponame, branch, uuid):
    """ Show status of a test
    """
    answer = models.logs.RepoTest.report(username, reponame, branch, uuid)
    return jsonify(answer)