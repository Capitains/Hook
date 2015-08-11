from flask import abort, jsonify, request
from app import app

import controllers.test
import models.logs
import json

# @app.route('/api/rest/v1.0/code/<username>/<reponame>/test', defaults= { "branch" : None})
def api_test_generate(username, reponame, branch=None):
    """ Generate a test on the machine

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    .:warning:. DISABLED
    """
    if branch is None:
        branch = request.form.get("branch")

    uuid, slug = controllers.test.launch(username, reponame, branch)

    return jsonify(
        id=uuid,
        repository=reponame,
        username=username,
        branch=branch,
        status="/api/rest/v1.0/code/{0}/{1}/{2}/test/{3}".format(username, reponame, slug, uuid)
    )

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<slug>/test/<uuid>')
def api_test_status(username, reponame, slug, uuid):
    """ Show status of a test
    """
    answer = models.logs.RepoTest.report(username, reponame, branch_slug=slug, uuid=uuid)
    return jsonify(answer)

@app.route('/api/rest/v1.0/code/<username>/<reponame>')
def api_repo_history(username, reponame):
    """ Return json history of previous tests
    """
    history = {
        "username" : username,
        "reponame" : reponame,
        "logs" :
        [
            {
                "run_at" : event.run_at,
                "uuid" : event.uuid,
                "coverage" : event.coverage,
                "ref" : event.branch,
                "slug" : event.branch_slug
            }
            for event in models.logs.RepoTest.objects(username__iexact=username, reponame__iexact=reponame)
        ]
    }
    return jsonify(history)

@app.route("/payload", methods=['POST'])
def api_test_payload():
    """ Handle GitHub payload 
    """
    payload = request.get_json(force=True)
    informations = {
        "sha" : request.headers.get("X-Hub-Signature"),
        "delivery" : request.headers.get("X-GitHub-Delivery"),
        "user" : request.headers.get("User-Agent")
    }

    username, reponame = tuple(payload["repository"]["full_name"].split("/"))
    event = request.headers.get("X-GitHub-Event")

    if event == "push":
        return api_test_generate(username, reponame, payload["ref"])
    elif event == "pull_request":
        return api_test_generate(username, reponame, payload["number"])


    return jsonify(
        headers=informations,
        payload=payload
    )