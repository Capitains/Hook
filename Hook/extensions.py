from flask.ext.mongoengine import MongoEngine 
from flask.ext.github import GitHub
from flask.ext.login import LoginManager

import yaml
import os

def read_yaml(path):
    with open(path) as f:
        c = yaml.load(f)
    return c[c["ENV"]], c["ENV"]

def write_env(conf, app):
    for key, value in conf.items():
        app.config[key] = value

db = MongoEngine()
github_api = GitHub()
login_manager = LoginManager()

conf, env = read_yaml(os.path.join(os.getcwd(), 'config.yaml'))

