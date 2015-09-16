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


@app.route('/repo/<username>/<reponame>', methods=["GET"])
def repo(username, reponame):
    kwargs = testctrl.read_repo(username, reponame, request)
    return render_template(
        'repo.html',
        **kwargs
    )

@app.route('/repo/<username>/<reponame>/<uuid>')
def repo_test_report(username, reponame, uuid):
    pass
    """
    repository = Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)
    test = RepoTest.objects.get_or_404(username__iexact=username, reponame__iexact=reponame, uuid=uuid)
    report = RepoTest.report(username, reponame, repo_test=test)

    return render_template(
        'report.html',
        report=report,
        repository=repository,
        test=test
    )
    """


@app.route("/api/github/payload", methods=['POST'])
def api_test_payload():
    """ Handle GitHub payload
    """
    return testctrl.hook_run(request, request.headers)


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
        return render_template(response), header, status
    else:
        return "", status, {}


@app.route('/api/rest/v1.0/code/<username>/<reponame>/cts.svg')
def repo_cts_status(username, reponame):
    """ Get a Badge for a repo """
    response, kwargs, status, header = testctrl.cts_badge(username, reponame, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
    if response:
        return render_template(response, **kwargs), header, status
    else:
        return "", status, {}


@app.route('/api/rest/v1.0/code/<username>/<reponame>/coverage.svg')
def repo_badge_coverage(username, reponame):
    """ Get a Badge for a repo """
    response, kwargs, status, header = testctrl.cts_badge(username, reponame, branch=request.args.get("branch"), uuid=request.args.get("uuid"))
    if response:
        return render_template(response, **kwargs), header, status
    else:
        return "", status, {}


@app.route('/api/rest/v1.0/code/<username>/<reponame>/test', defaults={"branch": None})
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
    return Hook.controllers.test_old.api_test_generate(username, reponame, branch, creator, gravatar, sha)

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<slug>/test/<uuid>', methods=["GET", "DELETE"])
def api_test_status(username, reponame, slug, uuid):
    """ Show status of a test
    """
    if request.method == "DELETE":
        test = Hook.models.RepoTest.objects.get_or_404(username__iexact=username, reponame__iexact=reponame, branch_slug__iexact=slug, uuid=uuid)
        Hook.controllers.test_old.remove(test.uuid)
        test.update(status=False, total=0, tested=0)
        test.git_status(True)
        return jsonify(cancelled=True)

    answer = Hook.models.RepoTest.report(username, reponame, slug=slug, uuid=uuid)
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
    return testctrl.history(username, reponame)