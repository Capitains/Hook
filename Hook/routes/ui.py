from flask import render_template
from models.logs import *

from app import app

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/repo/<username>/<reponame>')
def repo(username, reponame):
    repo = RepoTest.objects(username__iexact=username, reponame__iexact=reponame)
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