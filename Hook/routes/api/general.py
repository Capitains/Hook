from flask import jsonify
from models.logs import *

from app import app

@app.route('/api/rest/v1.0/code/<username>/<reponame>')
def api_repo_history(username, reponame):
    """ ???? """
    history = {
        "username" : username,
        "reponame" : reponame,
        "logs" :
        [
            {
                "run_at" : event.run_at,
                "uuid" : event.uuid,
                "coverage" : event.coverage
            }
            for event in RepoTest.objects(username__iexact=username, reponame__iexact=reponame)
        ]
    }
    return jsonify(history)