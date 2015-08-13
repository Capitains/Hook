from flask import jsonify, g, request, Response
from app import app
from flask.ext.login import login_required
import json

@app.route("/api/rest/v1.0/user/repositories", methods=["GET", "POST"])
@login_required
def api_user_repositories():

    if g.user:
        if request.method == "GET":
            response = json.dumps([repo.dict() for repo in g.user.repositories])
        elif request.method == "POST":
            response = json.dumps([repo.dict() for repo in g.user.fetch()])
        return Response(response=response,
                        status=200,
                        mimetype="application/json")
    else:
        return jsonify(None)

@app.route("/api/rest/v1.0/user/repositories/<owner>/<name>", methods=["PUT"])
@login_required
def api_user_repository_switch(owner, name):
    if g.user:
        return jsonify(status=g.user.switch(owner, name))
    else:
        return jsonify(status=False)