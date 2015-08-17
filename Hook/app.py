import os

from flask import Flask
from flask.ext.mongoengine import MongoEngine 
from flask.ext.github import GitHub
from flask.ext.login import LoginManager
from flask_environments import Environments

app = Flask(
    __name__,
    template_folder="../data/templates",
    static_folder="../data/static"
)
env = Environments(app)
env.from_yaml(os.path.join(os.getcwd(), 'config.yaml'))


db = MongoEngine(app)
github_api = GitHub(app)
login_manager = LoginManager(app)

from Hook.routes import ui
from Hook.routes import github
from Hook.routes import user
from Hook.routes.api import user as users
from Hook.routes.api import badges
from Hook.routes.api import test
import Hook.ui.templating