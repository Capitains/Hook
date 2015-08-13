from app import db, github_api, app
from flask import session, g, url_for
import datetime

class User(db.Document):
    """ User informations """
    uuid  = db.StringField(max_length=200, required=True)
    mail = db.StringField(required=True)
    login = db.StringField(required=True)
    git_id = db.IntField(required=True)
    github_access_token = db.StringField(max_length=200, required=True)
    refreshed = db.DateTimeField(default=datetime.datetime.now, required=True)

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

    def fetch(self):
        """ Fetch repositories informations 

        :returns: Indicator for cleaning and for update
        :rtype: Boolean, Boolean
        """
        if g.user == self:
            # We clear the old authors
            clean = self.clean()

            repos = github_api.get("user/repos", params={"affiliation": "owner,collaborator,organization_member", "access_token" : self.github_access_token}, all_pages=True)

            response = []
            for repo in repos:
                owner = repo["owner"]["login"]
                name  = repo["name"]

                repo_db = Repository.objects(owner=owner, name=name)
                if len(repo_db) > 0:
                    repo_db = repo_db.first()
                    repo_db.update(push__authors=self)
                else:
                    repo_db = Repository(owner=owner, name=name, authors=[self])
                    repo_db.save()
                response.append(repo_db)
        return response

    def clean(self):
        """ Remove list of repositories """
        if g.user == self:
            for repo in self.repositories:
                repo.update(pull__authors=self)
            return True
        return False


    @property
    def repositories(self):
        return list(Repository.objects(authors__in=[self]))

    @property
    def organizations(self):
        return Repository.objects(authors__in=[self]).distinct("owner")

    @property
    def testable(self):
        return Repository.objects(authors__in=[self], tested=True)

    def switch(self, owner, name):
        return Repository.switch(owner, name, self);
    
    def repository(self, owner, name):
        return Repository.objects(authors__in=[self], owner__iexact=owner, name__iexact=name)


class Repository(db.Document):
    """ Just as a cache of available repositories for user """
    owner  = db.StringField(max_length=200, required=True)
    name   = db.StringField(max_length=200, required=True)
    tested = db.BooleanField(default=False)
    hook_id = db.IntField(default=None)
    authors = db.ListField(db.ReferenceField(User))

    def dict(self):
        return {
            "owner" : self.owner,
            "name" : self.name
        }

    def isWritable(self):
        if g.user and g.user in self.authors:
            return True
        return False

    def switch(owner, name, user):
        repository = Repository.objects(authors__in=[user], owner__iexact=owner, name__iexact=name)
        if len(repository) > 0:
            repository = repository.first()
            tested = not repository.tested
            repository.update(tested=tested)
            return repository.hook()
        return None
    
    def hook(self):
        """ Create or delete hooks on GitHub API 

        :returns: Active status
        """
        uri = "repos/{owner}/{repo}/hooks".format(owner=self.owner, repo=self.name)
        payload = app.config["DOMAIN"] + url_for("api_test_payload")

        if self.tested is True:
            # Create hooks
            hook_data = {
              "name": "web",
              "active": True,
              "events": [
                "push",
                "pull_request"
              ],
              "config": {
                "url": payload,
                "content_type": "json",
                "secret": app.config["GITHUB_HOOK_SECRET"]
              }
            }
            hook = github_api.post(uri, data=hook_data)
            if "id" in hook:
                self.update(hook_id=hook["id"])
        else:
            uuid = None
            if self.hook_id is None:
                hooks = github_api.get(uri)
                hooks = [hook for hook in hooks if hook["config"]["url"] == payload]
                if len(hooks) == 0:
                    uuid = None
                else:
                    uuid = hooks[0]["id"]
            else:
                uuid = self.hook_id
            if uuid is not None:
                github_api.delete("repos/{owner}/{repo}/hooks/{id}".format(owner=self.owner, repo=self.name, id=uuid))

        self.reload()
        return self.tested