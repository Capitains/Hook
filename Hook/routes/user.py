from flask import session, url_for, redirect, g
from app import app, github_api, login_manager
from flask.ext.github import GitHub
from models.user import User


@app.route('/login/form')
def login():
    if session.get('user_id', None) is None:
        return github_api.authorize(scope=",".join(["user:email", "repo:status", "admin:repo_hook"]))
    else:
        redirect(url_for("index"))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/user')
def user():
    return str(github_api.get('user'))


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.objects.get(uuid=session['user_id'])

@login_manager.user_loader
def load_user(userid):
    return g.user