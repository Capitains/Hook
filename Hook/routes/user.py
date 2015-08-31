"""
    Routes for user oriented functions
"""
from flask import url_for, request
from Hook.app import app, userctrl


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
