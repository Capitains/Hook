#from flask import 
from app import app
from models.logs import *

from flask import make_response, render_template
import math 

def rnd(score):
    if score and score.coverage:
        return math.floor(score.coverage * 100) / 100

def build_template(resource):
    """ Induces the status template given a resource """
    if resource is None or resource.status is None:
        template = "svg/build.unknown.xml"
    elif resource.status is True:
        template = "svg/build.success.xml"
    else:
        template = "svg/build.failure.xml"
    return template

def coverage_template(resource):
    """ Induces the coverage template given a resource """
    if resource is None or resource.coverage is None:
        template = "svg/build.coverage.unknown.xml"
    elif resource.coverage > 90:
        template = "svg/build.coverage.success.xml"
    elif resource.coverage > 75:
        template = "svg/build.coverage.acceptable.xml"
    else:
        template = "svg/build.coverage.failure.xml"
    return template

def get_repo(**kwargs):
    """ Get the repo from the database """
    kwargs = {key+"__iexact":value for key, value in kwargs.items() if value is not None}
    if "uuid" in kwargs:
        repo = RepoTest.objects.get_or_404(**kwargs)
    else:
        repo = RepoTest.objects(**kwargs).first()
    return repo

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/status/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/status.svg', defaults = {"uuid" : None})
@app.route('/api/rest/v1.0/code/<username>/<reponame>/badge/status.svg', defaults = {"uuid" : None, "branch" : None})
def repo_badge_status(username, reponame, branch=None, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username=username, reponame=reponame, branch=branch, uuid=uuid)

    template = render_template(build_template(repo))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/coverage/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/coverage.svg', defaults = {"uuid" : None})
@app.route('/api/rest/v1.0/code/<username>/<reponame>/badge/coverage.svg', defaults = {"uuid" : None, "branch" : None})
def repo_badge_coverage(username, reponame, branch=None, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username=username, reponame=reponame, branch=branch, uuid=uuid)

    template = render_template(coverage_template(repo), score=rnd(repo))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/status/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/status.svg', defaults = {"uuid" : None})
@app.route('/api/rest/v1.0/code/<username>/<reponame>/badge/document/<path>/status.svg', defaults = {"uuid" : None, "branch" : None})
def doc_badge_status(username, reponame, path, branch=None, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username=username, reponame=reponame, branch=branch, uuid=uuid)

    parts = path.split(".")
    path = "/".join([username, reponame, "data", parts[0], parts[1], path])
    doc = repo.units.get(path=path)

    template = render_template(build_template(doc))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/coverage/<uuid>.svg')
@app.route('/api/rest/v1.0/code/<username>/<reponame>/<branch>/badge/document/<path>/coverage.svg', defaults = {"uuid" : None})
@app.route('/api/rest/v1.0/code/<username>/<reponame>/badge/document/<path>/coverage.svg', defaults = {"uuid" : None, "branch" : None})
def doc_badge_coverage(username, reponame, path, branch=None, uuid=None):
    """ Get a Badge for a repo """
    repo = get_repo(username=username, reponame=reponame, branch=branch, uuid=uuid)

    parts = path.split(".")
    path = "/".join([username, reponame, "data", parts[0], parts[1], path])
    doc = repo.units.get(path=path)

    template = render_template(coverage_template(doc), score=rnd(doc))
    response = make_response(template)
    response.content_type = 'image/svg+xml'

    return response

