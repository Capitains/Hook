from flask import Flask, g, session
from Hook.controller import UserCtrl, TestCtrl

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


userctrl = UserCtrl(api=github_api, db=db, g=g, session=session)
testctrl = TestCtrl(
    api=github_api,
    db=db,
    g=g,
    session=session,
    redis=app.config["REDIS_URL"],
    signature=app.config["GITHUB_HOOK_SECRET"],
    hooktest_path=app.config["HOOKTEST_PATH"],
    hooktest_secret=app.config["HOOKTEST_SECRET"],
    workers=app.config["HOOKTEST_WORKERS"],
    domain=app.config["DOMAIN"]
)

@app.before_request
def before_request():
    userctrl.before_request()
    testctrl.before_request()


@login_manager.user_loader
def load_user(user_id):
    """ Load a user

    :param userid: User id
    :return:
    """
    if hasattr(g, "user"):
        return g.user
    return None


@github_api.access_token_getter
def token_getter():
    if hasattr(g, "user"):
        user = g.user
        if user is not None:
            return user.github_access_token

from Hook.ui.templating import *
from Hook.routes import *