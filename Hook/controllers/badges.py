#from flask import 
from app import app
from models.logs import *

from flask import make_response, render_template
import math 

def rnd(score):
    return math.floor(score * 100) / 100

def build_template(resource):
    """ Induces the status template given a resource """
    if resource.status is True:
        template = "svg/build.success.xml"
    else:
        template = "svg/build.failure.xml"
    return template

def coverage_template(resource):
    """ Induces the coverage template given a resource """
    if resource.coverage > 90:
        template = "svg/build.coverage.success.xml"
    elif resource.coverage > 75:
        template = "svg/build.coverage.acceptable.xml"
    else:
        template = "svg/build.coverage.failure.xml"
    return template

def get_repo(username, reponame, branch, uuid):
    """ Get the repo from the database """
    if uuid is not None:
        repo = RepoTest.objects.get_or_404(username=username, reponame=reponame, branch=branch, uuid=uuid)
    else:
        repo = RepoTest.objects(username=username, reponame=reponame, branch=branch).first()

    return repo

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/status/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/status.svg', defaults = {"uuid" : None})
def repo_badge_status(username, reponame, branch, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username, reponame, branch, uuid)

    template = render_template(build_template(repo))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/coverage/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/coverage.svg', defaults = {"uuid" : None})
def repo_badge_coverage(username, reponame, branch, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username, reponame, branch, uuid)

    template = render_template(coverage_template(repo), score=rnd(repo.coverage))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/status/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/status.svg', defaults = {"uuid" : None})
def doc_badge_status(username, reponame, branch, path, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username, reponame, branch, uuid)

    parts = path.split(".")
    path = "/".join([username, reponame, "data", parts[0], parts[1], path])
    doc = repo.units.get(path=path)

    template = render_template(build_template(doc))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/coverage/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/coverage.svg', defaults = {"uuid" : None})
def doc_badge_coverage(username, reponame, branch, path, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username, reponame, branch, uuid)

    parts = path.split(".")
    path = "/".join([username, reponame, "data", parts[0], parts[1], path])
    doc = repo.units.get(path=path)

    template = render_template(coverage_template(doc), score=rnd(doc.coverage))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response