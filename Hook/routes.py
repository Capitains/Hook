from flask import url_for, request, render_template
from Hook.app import app, userctrl, testctrl


@app.route('/login/form')
def login():
    return userctrl.login(url_for("index"))


@app.route('/logout')
def logout():
    return userctrl.logout(url_for("index"))


@app.route('/api/github/callback')
@userctrl.api.authorized_handler
def authorized(access_token):
    next_uri = request.args.get('next') or url_for('index')
    return userctrl.authorize(access_token, request, success=next_uri, error=url_for("index"))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/repo/<username>/<reponame>', methods=["GET", "POST"])
def repo(username, reponame):
    kwargs = testctrl.read_repo(username, reponame, request)
    return render_template(
        'repo.html',
        **kwargs
    )

@app.route('/repo/<username>/<reponame>/<uuid>')
def repo_test_report(username, reponame, uuid):
    kwargs, status, header = testctrl.repo_report(username, reponame, uuid)
    if status == 200:
        return render_template("report.html", **kwargs)
    else:
        return kwargs, status, header


@app.route("/api/github/payload", methods=['POST'])
def api_test_payload():
    """ Handle GitHub payload
    """
    return testctrl.handle_payload(request, request.headers, callback_url=url_for("api_hooktest_log", _external=True))


@app.route("/api/hooktest", methods=["POST"])
def api_hooktest_log():
    """
    :return:d
    """
    return "", testctrl.handle_hooktest_log(request), {}


@app.route("/api/rest/v1.0/user/repositories", methods=["GET", "POST"])
def api_user_repositories():
    return userctrl.fetch(request.method)


@app.route("/api/rest/v1.0/user/repositories/<owner>/<name>", methods=["PUT"])
def api_user_repository_switch(owner, name):
    return testctrl.link(owner, name, url_for("api_test_payload"))


@app.route('/api/rest/v1.0/code/<username>/<reponame>/status.svg')
def repo_badge_status(username, reponame):
    """ Get a Badge for a repo """
    response, status, header = testctrl.status_badge(username, reponame, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
    if response:
        return render_template(response), status, header
    else:
        return "", status, {}


@app.route('/api/rest/v1.0/code/<username>/<reponame>/cts.svg')
def repo_cts_status(username, reponame):
    """ Get a Badge for a repo """
    response, kwargs, status, header = testctrl.cts_badge(username, reponame, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
    if response:
        return render_template(response, **kwargs), status, header
    else:
        return "", status, {}


@app.route('/api/rest/v1.0/code/<username>/<reponame>/coverage.svg')
def repo_badge_coverage(username, reponame):
    """ Get a Badge for a repo """
    response, kwargs, status, header = testctrl.coverage_badge(username, reponame, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
    if response:
        return render_template(response, **kwargs), status, header
    else:
        return "", status, {}


@app.route('/api/rest/v1.0/code/<username>/<reponame>/test')
def api_test_generate_route(username, reponame):
    """ Generate a test on the machine

    :param username: Name of the user
    :type username: str
    :param repository: Name of the repository
    :type repository: str
    :param branch: branch to be tested
    :type branch: str

    .:warning:. DISABLED
    """
    return testctrl.generate(username, reponame, callback_url=url_for("api_hooktest_log", _external=True))


@app.route('/api/rest/v1.0/code/<username>/<reponame>', methods=["GET", "DELETE"])
def api_repo_history(username, reponame):
    """ Return json history of previous tests
    """
    if request.method == "DELETE":
        return testctrl.cancel(username, reponame, uuid=request.args.get("uuid"))
    elif request.args.get("uuid"):
        return testctrl.repo_report(
            username,
            reponame,
            uuid=request.args.get("uuid"),
            start=request.args.get("start", 0, type=int),
            limit=request.args.get("limit", None, type=int),
            json=True
        )
    else:
        return testctrl.history(username, reponame)


@app.route('/api/rest/v1.0/code/<username>/<reponame>/unit', methods=["GET"])
def api_repo_unit_history(username, reponame):
    """ Return json representation of one unit test
    """
    return testctrl.repo_report_unit(
        username,
        reponame,
        uuid=request.args.get("uuid"),
        unit=request.args.get("unit", "all")
    )