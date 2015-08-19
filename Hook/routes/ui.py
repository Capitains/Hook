from flask import render_template, request

from Hook.app import app
from Hook.models.github import Repository, RepoTest


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login_ui():
    return render_template('login.html')


@app.route('/repo/<username>/<reponame>', methods=["GET", "POST"])
def repo(username, reponame):
    repository = Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)

    if request.method == "POST" and hasattr(g, "user") and g.user in repository.authors:
        repository.config(request.form)

    tests = RepoTest.objects(username__iexact=repository.owner, reponame__iexact=repository.name)
    for test in tests:
        test.branch = test.branch.split("/")[-1]

    done = [test for test in tests if test.status is not None]
    running = [test for test in tests if test.status is None]

    for r in running:
        if r.total > 0:
            r.percent = int(r.tested / r.total * 100)
        else:
            r.percent = 0

    return render_template(
        'repo.html',
        repository=repository,
        tests=done,
        running=running
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

