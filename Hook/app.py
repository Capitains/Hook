from flask import Flask
from flask.ext.mongoengine import MongoEngine 

app = Flask(
    __name__,
    template_folder="../data/templates",
    static_folder="../data/static"
)

app.config["MONGODB_SETTINGS"] = {'DB': "Hook2"}
app.config["SECRET_KEY"] = "KeepThisS3cr3t"

db = MongoEngine(app)

from controllers import ui
from controllers.api import general
from controllers.api import badges
from controllers.api import test