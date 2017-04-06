from json import load, loads
from os.path import isfile
from glob import glob


def make_fixture(token="yup"):
    fixtures = {}
    for file in glob("./tests/fixtures/*.response.json"):
        with open(file) as f:
            fixtures[file] = [load(f)]
        if isfile(file.replace("response", "header")):
            with open(file.replace("response", "header")) as f2:
                fixtures[file].append(loads(f2.read().replace("{{access_token}}", token)))
    return fixtures