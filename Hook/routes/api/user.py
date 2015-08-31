import json
from flask import jsonify, g, request, Response

import Hook.controllers.github
from Hook.app import app


@app.route("/api/rest/v1.0/user/repositories", methods=["GET", "POST"])
def api_user_repositories():
    if hasattr(g, "user") and g.user:
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
def api_user_repository_switch(owner, name):
    if hasattr(g, "user") and g.user:
        return jsonify(status=g.user.switch(owner, name, Hook.controllers.github.hook))
    else:
        return jsonify(status=False)
