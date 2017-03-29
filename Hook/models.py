__author__ = 'Thibault Clerice'

import datetime
import re



pr_finder = re.compile("pull\/([0-9]+)\/head")


def model_maker(db, prefix=""):
    """ Creates model based on Database connection

    :param db: Flask SQLAlchemy Database instance
    :type db: flask_sqlalchemy.SQLAlchemy
    :return: Models
    """

    RepoOwnership = db.Table("repoownership",
        db.Column('user_uuid', db.Integer, db.ForeignKey('user.uuid')),
        db.Column('repo_uuid', db.Integer, db.ForeignKey('repository.uuid'))
    )

    class User(db.Model):
        """ User information

        :param uuid: User Unique Identifier
        :type uuid: int
        :param email: Email of the user
        :type email: str
        :param login: Nickname of the user
        :type login: str
        :param git_id: Git Identifier
        :type git_id: int
        :param github_access_token: Github Access Token
        :type github_access_token: str
        :param refreshed: Last refreshed repositories
        :type refreshed: datetime

        """
        uuid = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(255), unique=True, nullable=False)
        login = db.Column(db.String(255), unique=True, nullable=False)
        git_id = db.Column(db.Integer)
        github_access_token = db.Column(db.String(200), nullable=False)
        refreshed = db.Column(db.Date(), default=None)
        repositories = db.relationship(
            'Repository', secondary=RepoOwnership,
            backref=db.backref('repository', lazy='dynamic')
        )

        def __eq__(self, other):
            return isinstance(other, self.__class__) and other.uuid == self.uuid

        @property
        def is_anonymous(self):
            return False

        @property
        def is_authenticated(self):
            return True

        @property
        def is_active(self):
            return True

        def remove_authorship(self):
            """ Remove list of repositories """
            for repo in self.repositories:
                repo.update(pull__authors=self)

        @property
        def organizations(self):
            return Repository.objects(authors__in=[self]).distinct("owner")

        @property
        def testable(self):
            return Repository.objects(authors__in=[self], tested=True)

        def switch(self, owner, name, callback):
            return Repository.switch(owner, name, self, callback)

        def repository(self, owner, name, author):
            return Repository.objects(authors__in=[self], owner__iexact=owner, name__iexact=name)

        def addto(self, owner, name):
            """ Add the user to the authors of a repository. Create
                Create the repository if required

            :param owner: Owner name of the repository
            :type owner: str
            :param name: Name of the repository
            :type name: str

            :return: New or Updated repository
            :rtype: Repository
            """
            repo_db = Repository.objects(owner__iexact=owner, name__iexact=name)
            if len(repo_db) > 0:
                repo_db = repo_db.first()
                repo_db.update(push__authors=self)
            else:
                repo_db = Repository(owner=owner, name=name, authors=[self])
                repo_db.save()

            return repo_db

    class Repository(db.Model):
        """ Just as a cache of available repositories for user """
        uuid = db.Column(db.Integer, primary_key=True)
        owner = db.Column(db.String(200), nullable=False)
        name = db.Column(db.String(200), nullable=False)
        active = db.Column(db.Boolean, nullable=False, default=False)
        users = db.relationship(
            'User', secondary=RepoOwnership,
            backref=db.backref('user', lazy='dynamic')
        )

        @property
        def full_name(self):
            return self.owner + "/" + self.name

        def dict(self):
            return {
                "owner": self.owner,
                "name": self.name
            }

        def isWritable(self, user):
            if user in self.authors:
                return True
            return False

        @staticmethod
        def find_or_create(owner, name, active=False, _commit_on_create=True):
            """ Finds a repository or creates it

            :param owner: Name of the repo owner
            :param name: Name of the repository
            :param active: Whether this is actively receiving tests results
            :param _commit_on_create: Automatically commit if we created the repo
            :return:
            """
            query = Repository.query.filter_by(owner=owner, name=name, active=active)
            repo = query.first()
            if not (repo):
                repo = Repository(owner=owner, name=name, active=active)
                if _commit_on_create is True:
                    db.session.commit()
            return repo

    class RepoTest(db.Model):
        """ Complete repository status """
        uuid = db.Column(db.Integer, primary_key=True)
        run_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        branch = db.Column(db.String, nullable=None)

        travis_uri = db.Column(db.String, nullable=False)
        travis_build_id = db.Column(db.String(10), nullable=False)
        travis_user = db.Column(db.String(200), nullable=False)
        travis_user_gravatar = db.Column(db.String(200), nullable=False)

        texts_total = db.Column(db.Integer, nullable=False, default=0)
        texts_passing = db.Column(db.Integer, nullable=False, default=0)
        metadata_total = db.Column(db.Integer, nullable=False, default=0)
        metadata_passing = db.Column(db.Integer, nullable=False, default=0)
        coverage = db.Column(db.Float, nullable=False, default=0.0)
        nodes_count = db.Column(db.Integer, nullable=False, default=0)
        words_count = db.Column(db.Integer, nullable=True)

    return User, Repository, RepoTest, RepoOwnership
