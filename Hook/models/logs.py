import datetime
from app import db


class DocLogs(db.Document):
    """ Unittest level logs """
    title  = db.StringField(max_length=255, required=True)
    status = db.BooleanField(required=False)


class DocTest(db.Document):
    """ Complete Document level status"""
    path = db.StringField(required=True)
    status = db.BooleanField(required=True)
    coverage = db.FloatField(min_value=0.0, max_value=100.0, required=True)
    logs = db.ListField(db.EmbeddedDocumentField("DocLogs"))


class RepoLogs(db.Document):
    text = db.StringField(required=True)


class RepoTest(db.Document):
    """ Complete repository status """
    run_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    uuid = db.StringField(required=True)
    username = db.StringField(required=True)
    reponame = db.StringField(required=True)
    userrepo = db.StringField(required=True)
    branch = db.StringField(required=True)
    status = db.BooleanField(required=True)
    coverage = db.FloatField(min_value=0.0, max_value=100.0, required=True)
    logs = db.ListField(db.EmbeddedDocumentField("RepoLogs"))
    units = db.ListField(db.EmbeddedDocumentField("DocTest"))