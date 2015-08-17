from app import app, github_api

from uuid import uuid4
from flask import jsonify, request, redirect, session, url_for, g
from models.user import User
import routes.api.test 
import controllers.test

@app.route("/api/github/payload", methods=['POST'])
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
        creator = payload["head_commit"]["committer"]["username"]
        gravatar = "https://avatars.githubusercontent.com/{0}".format(creator)
        sha = payload["head_commit"]["id"]
        return controllers.test.api_test_generate(username, reponame, payload["ref"], creator, gravatar, sha, github=True)
    elif event == "pull_request" and payload["action"] in ["reopened", "opened"]:
        creator = payload["pull_request"]["user"]["login"]
        gravatar = "https://avatars.githubusercontent.com/{0}".format(creator)
        sha = payload["pull_request"]["head"]["sha"]
        return controllers.test.api_test_generate(username, reponame, payload["number"], creator, gravatar, sha, github=True)

    return jsonify(
        headers=informations,
        payload=payload
    )


@app.route('/api/github/callback')
@github_api.authorized_handler
def authorized(access_token):
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        return redirect(next_url)

    user = User.objects(github_access_token=access_token)

    if len(user) == 0:
        # Need to retrieve information HERE
        more = github_api.get("user", params={"access_token" : access_token})
        user = User(
            uuid=str(uuid4()),
            github_access_token=access_token,
            mail=more["email"],
            git_id=more["id"],
            login=more["login"]
        )
    else:
        user = user.first()

    user.github_access_token = access_token
    user.save()

    session['user_id'] = user.uuid
    return redirect(next_url)


@github_api.access_token_getter
def token_getter():
    user = g.user
    if user is not None:
        return user.github_access_token