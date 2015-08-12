from app import db
from flask import session, g

class User(db.Document):
    """ User informations """
    uuid  = db.StringField(max_length=200, required=True)
    mail = db.StringField(required=True)
    login = db.StringField(required=True)
    git_id = db.IntField(required=True)
    github_access_token = db.StringField(max_length=200, required=True)


    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.uuid == self.uuid

    def is_authenticated(self):
        """ Check that the user is authenticated """
        return self == g.user

    def is_anonymous(self):
        return False

    def is_active(self):
        return True
    
    def get_id(self):
        return self.uuid
    