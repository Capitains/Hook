from flask import abort, jsonify, request, g, Response
from app import app, github_api
from flask.ext.login import login_required

import controllers.test
import models.logs
import models.user
import json

@app.route('/api/rest/v1.0/code/<username>/<reponame>/test', defaults= { "branch" : None})
@login_required
def api_test_generate_route(username, reponame, branch=None, creator=None, gravatar=None, sha=None):
    """ Generate a test on the machine

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    .:warning:. DISABLED
    """
    return controllers.test.api_test_generate(username, reponame, branch, creator, gravatar, sha)

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<slug>/test/<uuid>', methods=["GET", "DELETE"])
def api_test_status(username, reponame, slug, uuid):
    """ Show status of a test
    """
    if request.method == "DELETE":
        test = models.logs.RepoTest.objects.get_or_404(username__iexact=username, reponame__iexact=reponame, branch_slug__iexact=slug, uuid=uuid)
        controllers.test.remove(test.uuid)
        test.update(status=False, total=0, tested=0)
        test.git_status(True)
        return jsonify(cancelled=True)

    answer = models.logs.RepoTest.report(username, reponame, slug=slug, uuid=uuid)
    line = request.args.get("from")
    if line:
        line = int(line)
        if len(answer["logs"]) > line + 3:
            answer["logs"] = answer["logs"][line:]
        else:
            answer["logs"] = []
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