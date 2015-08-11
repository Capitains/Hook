from flask import Flask
from flask.ext.mongoengine import MongoEngine 

app = Flask(
    __name__,
    template_folder="../data/templates",
    static_folder="../data/static"
)

app.config["MONGODB_SETTINGS"] = {'DB': "Hook4"}
app.config["SECRET_KEY"] = "KeepThisS3cr3t"

db = MongoEngine(app)

from routes import ui
from routes.api import general
from routes.api import badges
from routes.api import test