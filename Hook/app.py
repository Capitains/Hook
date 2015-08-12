from flask import Flask
from flask.ext.mongoengine import MongoEngine 
from flask.ext.github import GitHub
from flask.ext.login import LoginManager
from flask_environments import Environments
import os

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

from routes import ui
from routes import github
from routes import user
from routes.api import general
from routes.api import badges
from routes.api import test
from routes import github
from routes import user