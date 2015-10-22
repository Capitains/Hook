import yaml
import logging
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.log import access_log, app_log, gen_log
from Hook.ext import HookUI
from flask import Flask


def read_yaml(path):
    with open(path) as f:
        c = yaml.load(f)
    return c[c["ENV"]], c["ENV"]


def set_logging(level, name, path, logger):
    """ Reroute logging of tornado into specified file with a RotatingFileHandler

    :param level: Level of logging
    :type level: str
    :param name: Name of logs file
    :param path: Path where to store the logs file
    :param logger: logging.logger object of Tonardo
    """
    log_level = getattr(logging, level.upper())
    handler = logging.handlers.RotatingFileHandler("{0}/{1}".format(path, name), maxBytes=3145728, encoding="utf-8", backupCount=5)
    handler.setLevel(log_level)
    logger.addHandler(handler)


def generate_app(
         debug=False, config_file=None, secret="",
         session_secret="",
         github_client_id="", github_client_secret="", github_hook_secret="",
         mongodb_db="Hook", mongodb_host='127.0.0.1', mongodb_port=27017, mongodb_user=None, mongodb_password=None,
         hooktest_secret="", hooktest_remote="http://127.0.0.1:5002/hooktest/rest/api/queue"
    ):
    app = Flask(__name__)
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    if not config_file:
        app.config["SECRET_KEY"] = session_secret,
        app.config["GITHUB_CLIENT_ID"] = github_client_id
        app.config["GITHUB_CLIENT_SECRET"] = github_client_secret

        app.config["MONGODB_DB"]= mongodb_db
        app.config['MONGODB_HOST'] = mongodb_host
        app.config['MONGODB_PORT'] = mongodb_port

        if mongodb_user:
            app.config['MONGODB_USERNAME'] = mongodb_user
        if mongodb_password:
            app.config['MONGODB_PASSWORD'] = mongodb_password

        app.config["HOOKUI_HOOKTEST_SECRET"] = hooktest_secret
        app.config["HOOKUI_GITHUB_SECRET"] = github_hook_secret
        app.config["HOOKUI_REMOTE"] = hooktest_remote
    else:
        app.config.update(read_yaml(config_file)[0])

    app.debug = debug
    app.config["DEBUG"] = debug
    hook = HookUI(prefix="", app=app)
    return app

def run(level="WARNING", port=5000, path=None, **kwargs):
    """ Set up a Tornado process around a flask app for quick run of the WorkerAPI Blueprint

    :param secret: Salt to use in encrypting the body
    :param debug: Set Flask App in debug Mode
    :param port: Port to use for Flask App
    :param path: Path where to store the logs
    :param level: Level of Log
    :param git: Pather where to clone the data
    :param worker: Number of worker to use for HookTest runs
    """
    app = generate_app(**kwargs)

    http_server = HTTPServer(WSGIContainer(app))
    http_server.bind(port)
    http_server.start(0)

    if path:
        set_logging(level, "tornado.access", path, access_log)
        set_logging(level, "tornado.application", path, app_log)
        set_logging(level, "tornado.general", path, gen_log)

    IOLoop.current().start()

if __name__ == "__main__":
    run()