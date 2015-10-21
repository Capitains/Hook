import yaml
import os

def read_yaml(path):
    with open(path) as f:
        c = yaml.load(f)
    return c[c["ENV"]], c["ENV"]

def write_env(conf, app):
    for key, value in conf.items():
        app.config[key] = value

conf, env = read_yaml(os.path.join(os.path.dirname(__file__), '../config.yaml'))