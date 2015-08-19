import datetime

from flask import g

from Hook.app import db
import Hook.models.github


class User(db.Document):
    """ User information """
    uuid  = db.StringField(max_length=200, required=True)
    mail = db.StringField(required=False)
    login = db.StringField(required=True)
    git_id = db.IntField(required=True)
    github_access_token = db.StringField(max_length=200, required=True)
    refreshed = db.DateTimeField(default=datetime.datetime.now, required=True)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.uuid == self.uuid

    def is_authenticated(self):
        """ Check that the user is authenticated """
        return hasattr(g, "user") and self == g.user

    def is_anonymous(self):
        return False

    def is_active(self):
        return True
    
    def get_id(self):
        return self.uuid

    def clean(self):
        """ Remove list of repositories """
        if hasattr(g, "user") and g.user == self:
            for repo in self.repositories:
                repo.update(pull__authors=self)
            return True
        return False

    @property
    def repositories(self):
        return list(Hook.models.github.Repository.objects(authors__in=[self]))

    @property
    def organizations(self):
        return Hook.models.github.Repository.objects(authors__in=[self]).distinct("owner")

    @property
    def testable(self):
        return Hook.models.github.Repository.objects(authors__in=[self], tested=True)

    def switch(self, owner, name):
        return Hook.models.github.Repository.switch(owner, name, self)
    
    def repository(self, owner, name):
        return Hook.models.github.Repository.objects(authors__in=[self], owner__iexact=owner, name__iexact=name)

    def addto(self, owner, name):
        """ Add the user to the authors of a repository. Create
            Create the repository if required

        :param owner: Owner name of the repository
        :type owner: str
        :param name: Name of the repository
        :type name: str

        :return: New or Updated repository
        :rtype: Hook.models.github.Repository
        """
        repo_db = self.repository(owner=owner, name=name)
        if len(repo_db) > 0:
            repo_db = repo_db.first()
            repo_db.update(push__authors=self)
        else:
            repo_db = Hook.models.github.Repository(owner=owner, name=name, authors=[self])
            repo_db.save()
        return repo_db
