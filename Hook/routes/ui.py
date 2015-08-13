from flask import render_template, Markup
from models.logs import *
from models.user import Repository

from app import app
from utils import slugify

@app.template_filter('slugify')
def _slugify(string):
    if not string:
        return ""
    return slugify(string)

@app.template_filter('checked')
def _bool(boolean):
    if boolean:
        return " checked "
    return ""

@app.template_filter('btn')
def _bool(boolean):
    if boolean:
        return "btn-success"
    return "btn-danger"

@app.template_filter('format_log')
def _format_log(string):
    if not string:
        return ""
    else:
        if string.startswith(">>>> "):
            string = Markup("<b>{0}</b>".format(string.strip(">")))
        elif string.startswith(">>>>> "):
            string = Markup("<i>\t{0}</i>".format(string.strip(">")))
        elif string.startswith(">>> "):
            string = Markup("<u>{0}</u>".format(string.strip(">")))
        elif string.startswith("[success]"):
            string = Markup("<span class='success'>{0}</span>".format(string.strip("[success]")))
        elif string.startswith("[failure]"):
            string = Markup("<span class='failure'>{0}</span>".format(string.strip("[failure]")))
        return string

@app.template_filter('success_class')
def _success_class(status):
    string = ""
    try:
        if status is True:
            string = "success"
        elif status is False:
            string = "failure"
    except:
        string = ""
    finally:
        return string

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_ui():
    return render_template('login.html')

@app.route('/repo/<username>/<reponame>')
def repo(username, reponame):
    repository = Repository.objects.get_or_404(owner__iexact=username, name__iexact=reponame)

    tests = RepoTest.objects(username__iexact=repository.owner, reponame__iexact=repository.name)
    for test in tests:
        test.branch = test.branch.split("/")[-1]

    done = [test for test in tests if test.tested == test.total]
    running = [test for test in tests if test.tested != test.total]

    for r in running:
        r.percent = int(r.tested / r.total * 100)

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

