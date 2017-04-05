from werkzeug.exceptions import Forbidden


class ModelException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super(ModelException, self).__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload


class RightsException(ModelException, Forbidden):
    status_code = 403
