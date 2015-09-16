from flask import render_template, request

from Hook.app import app, testctrl, userctrl


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
    repository = Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)
    test = RepoTest.objects.get_or_404(username__iexact=username, reponame__iexact=reponame, uuid=uuid)
    report = RepoTest.report(username, reponame, repo_test=test)

    return render_template(
        'report.html',
        report=report,
        repository=repository,
        test=test
    )

