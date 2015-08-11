from flask import render_template, Markup
from models.logs import *

from app import app
from utils import slugify

@app.template_filter('slugify')
def _slugify(string):
    if not string:
        return ""
    return slugify(string)

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
    return render_template('login.html')

@app.route('/repo/<username>/<reponame>')
def repo(username, reponame):
    repo = RepoTest.objects(username__iexact=username, reponame__iexact=reponame)
    for r in repo:
        r.branch = r.branch.split("/")[-1]
    done = [r for r in repo if r.tested == r.total]
    running = [r for r in repo if r.tested != r.total]



    for r in running:
        r.percent = int(r.tested / r.total * 100)

    return render_template(
        'repo.html',
        username=username,
        reponame=reponame,
        tests=done,
        running=running
    )

@app.route('/repo/<username>/<reponame>/<uuid>')
def repo_test_report(username, reponame, uuid):
    repo_test = RepoTest.objects.get_or_404(username__iexact=username, reponame__iexact=reponame, uuid=uuid)
    report = RepoTest.report(username, reponame, repo_test=repo_test)

    return render_template(
        'report.html',
        report=report,
        repo=repo_test
    )