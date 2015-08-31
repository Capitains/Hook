from Hook.app import app, testctrl
from flask import url_for, request


@app.route("/api/github/payload", methods=['POST'])
def api_test_payload():
    """ Handle GitHub payload 
    """
    return testctrl.hook_run(request, request.headers)
