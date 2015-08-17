import os

from flask import Flask

app = Flask(
    __name__,
    template_folder="../data/templates",
    static_folder="../data/static"
)

# Extension setting
from Hook.extensions import *

write_env(conf, app)

db.init_app(app)
github_api.init_app(app)
login_manager.init_app(app)

from Hook.routes import ui
from Hook.routes import github
from Hook.routes import user
from Hook.routes.api import user as users
from Hook.routes.api import badges
from Hook.routes.api import test
import Hook.ui.templating