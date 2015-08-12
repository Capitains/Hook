from flask import jsonify, g, request
from app import app
from flask.ext.login import login_required
import json

@app.route("/api/rest/v1.0/user/repositories", methods=["GET", "POST"])
@login_required
def api_user_repositories():
    if g.user:
        if request.method == "GET":
            return json.dumps([repo.dict() for repo in g.user.repositories])
        elif request.method == "POST":
            return json.dumps([repo.dict() for repo in g.user.fetch()])
    else:
        return jsonify(None)