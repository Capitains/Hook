__author__ = 'Thibault Clerice'

import datetime
import re
from Hook.exceptions import *
from deepdiff import DeepDiff
from math import isclose


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
        git_id = db.Column(db.String(255))
        github_access_token = db.Column(db.String(200), nullable=False)
        refreshed = db.Column(db.Date(), default=None)
        repositories = db.relationship(
            'Repository', secondary=RepoOwnership,
            backref=db.backref('repository', lazy='dynamic')
        )
        dyn_repositories = db.relationship(
            'Repository', secondary=RepoOwnership, lazy="dynamic",
            backref=db.backref('dyn_repository', lazy='dynamic')
        )

        def __eq__(self, other):
            return isinstance(other, self.__class__) and other.uuid == self.uuid

        @property
        def organizations(self):
            return [
                owner
                for owner, *_ in self.dyn_repositories.
                    group_by(Repository.owner).
                    filter(Repository.owner != self.login).
                    with_entities(Repository.owner).
                    all()
            ]

        @property
        def active_repositories(self):
            return self.dyn_repositories.filter(Repository.active == True).all()

        def __repr__(self):
            return self.login

    class Repository(db.Model):
        """ Just as a cache of available repositories for user """
        uuid = db.Column(db.Integer, primary_key=True)
        owner = db.Column(db.String(200), nullable=False)
        name = db.Column(db.String(200), nullable=False)
        active = db.Column(db.Boolean, nullable=False, default=False)
        main_branch = db.Column(db.String(200), nullable=False, default="master")
        users = db.relationship(
            'User', secondary=RepoOwnership,
            backref=db.backref('user', lazy='dynamic')
        )
        tests = db.relationship(
            "RepoTest",
            backref=db.backref('repo_test'), lazy='dynamic'
        )

        @property
        def full_name(self):
            return self.owner + "/" + self.name

        def __repr__(self):
            return self.full_name

        def dict(self):
            return {
                "owner": self.owner,
                "name": self.name
            }

        @property
        def last_master_test(self):
            return self.tests.\
                filter(RepoTest.branch == self.main_branch).\
                order_by(RepoTest.run_at.desc()).\
                first()

        def has_rights(self, user):
            """ Check that a user has rights to switch value on given repo

            :param user: User whose rights are checked
            :type user: User
            :return: Rights status
            :rtype: bool
            """
            if user in self.users:
                return True
            return False

        def switch_active(self, user, _commit=True):
            """ Switch the ability to receive Hooktest data

            :param user: User performing action
            :param _commit: Force commit
            :return: Current status
            :rtype: bool
            """
            if self.has_rights(user):
                self.active = not self.active
                if _commit is True:
                    db.session.commit()
                return self.active
            raise RightsException("{} has no rights to write over {}".format(user, self))

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

        def register_test(
                self, branch, travis_uri, travis_build_id, travis_user, travis_user_gravatar, texts_total,
                texts_passing, metadata_total, metadata_passing, coverage, nodes_count,
                units, words_count=None
        ):
            """ Save a test and produce a diff if this is master

            :param branch: branch
            :type branch: Str
            :param travis_uri: travis_uri
            :type travis_uri: Str
            :param travis_build_id: travis_build_id
            :type travis_build_id: Str
            :param travis_user: travis_user
            :type travis_user: Str
            :param travis_user_gravatar: travis_user_gravatar
            :type travis_user_gravatar: Str
            :param texts_total: texts_total
            :type texts_total: Int
            :param texts_passing: texts_passing
            :type texts_passing: Int
            :param metadata_total: metadata_total
            :type metadata_total: Int
            :param metadata_passing: metadata_passing
            :type metadata_passing: Int
            :param coverage: coverage
            :type coverage: Flo
            :param nodes_count: nodes_count
            :type nodes_count: Int
            :param units: Dictionary Path->Status
            :type units: dict
            :return:
            """
            repo = RepoTest(
                repository=self.uuid, branch=branch, travis_uri=travis_uri,
                travis_build_id=travis_build_id, travis_user=travis_user, travis_user_gravatar=travis_user_gravatar,
                texts_total=texts_total, texts_passing=texts_passing, metadata_total=metadata_total,
                metadata_passing=metadata_passing, coverage=coverage, nodes_count=nodes_count
            )

            diff = repo.diff(self.last_master_test, units, words_count)

            if words_count is not None:
                repo.save_words_count(words_count, _commit=True)
            if branch == self.main_branch:
                repo.save_units(units, _commit=True)

            db.session.commit()
            return repo, diff

    class RepoTest(db.Model):
        """ Complete repository status """
        uuid = db.Column(db.Integer, primary_key=True)
        repository = db.Column(db.Integer, db.ForeignKey('repository.uuid'), nullable=False)

        run_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        branch = db.Column(db.String(250), nullable=None)

        travis_uri = db.Column(db.String(2000), nullable=False)
        travis_build_id = db.Column(db.String(10), nullable=False)
        travis_user = db.Column(db.String(200), nullable=False)
        travis_user_gravatar = db.Column(db.String(2000), nullable=False)

        texts_total = db.Column(db.Integer, nullable=False, default=0)
        texts_passing = db.Column(db.Integer, nullable=False, default=0)
        metadata_total = db.Column(db.Integer, nullable=False, default=0)
        metadata_passing = db.Column(db.Integer, nullable=False, default=0)
        coverage = db.Column(db.Float, nullable=False, default=0.0)
        nodes_count = db.Column(db.Integer, nullable=False, default=0)

        units = db.relationship(
            "UnitTest",
            backref=db.backref('unit_test')
        )
        words_count = db.relationship(
            "WordCount",
            backref=db.backref('word_count')
        )

        dyn_units = db.relationship(
            "UnitTest",
            backref=db.backref('unit_test_dyn'), lazy="dynamic"
        )
        dyn_words = db.relationship(
            "WordCount",
            backref=db.backref('word_count_dyn'), lazy="dynamic"
        )

        def __repr__(self):
            return self.travis_build_id

        def save_units(self, unit_dict, _force_clear=True, _commit=True):
            """ Save a dictionary of units in the database

            :param unit_dict:
            :param _force_clear: Force removal of former scores
            :param _commit: Automatically commit
            :return:
            """
            if _force_clear:
                # We need to do something
                _ = 0
            for path, status in unit_dict.items():
                u = UnitTest(path=path, status=status)
                self.units.append(u)
            if _commit is True:
                db.session.commit()

        def save_word_counts(self, words_count, _commit=True):
            """ Save a dictionary of units in the database

            :param words_count: Key-value pairs of lang code + word count
            :param _commit: Automatically commit
            :return:
            """
            for lang, count in words_count.items():
                u = WordCount(lang=lang, count=count)
                self.words_count.append(u)
            if _commit is True:
                db.session.commit()

        def get_unit(self, path):
            """ Retrieve a unit given a path

            :param path: Path of the unit
            :return: Status
            """
            data = self.dyn_units.filter(UnitTest.path == path).first()
            if data is not None:
                return data.status

        def diff(self, last_master, units, words_count):
            """ Compute the diff between two repos given another repo and current repo units and word count

            :param last_master: Last Master Test
            :type last_master: RepoTest
            :param units:
            :param words_count:
            :return:
            """
            items = [
                (self.dict, last_master.dict, "Global"),
                (units, last_master.units_as_dict, "Units"),
                (words_count, last_master.words_count_as_dict, "Words")
            ]
            ret = {}
            for me, you, name in items:
                current = []
                complete_keys = set(list(me.keys()) + list(you.keys()))
                for key in complete_keys:
                    if key not in you:
                        current.append(self.new_object(key))
                        if isinstance(me[key], bool):
                            current.append(self.pass_fail_object(key, me[key]))
                    elif key not in me:
                        current.append(self.del_object(key))
                    elif me[key] != you[key]:
                        if isinstance(me[key], bool):
                            current.append(self.pass_fail_object(key, me[key]))
                        elif isinstance(me[key], bool):
                            if not isclose(me[key], you[key], 0.0001):
                                current.append(self.diff_int_object(key, me[key] - you[key]))
                        else:
                            current.append(self.diff_int_object(key, me[key]-you[key]))
                ret[name] = current
            return ret


        @staticmethod
        def readableDiff(*dicts):
            """ Compute the diff between two repos given another repo and current repo units and word count

            :param dicts: DeepDiff output
            :type last_master: RepoTest
            :param units:
            :param words_count:
            :return:
            """
            for diff in dicts:
                if "values_changed" in diff:
                    for key, value in diff["values_changed"].items():
                        yield key.replace("root['", "").replace("']", "")

        @property
        def dict(self):
            return {
                "texts_total": self.texts_total,
                "texts_passing": self.texts_passing,
                "metadata_total": self.metadata_total,
                "metadata_passing": self.metadata_passing,
                "coverage": self.coverage,
                "nodes_count": self.nodes_count,
            }

        @staticmethod
        def new_object(name):
            return "New", name, ""

        @staticmethod
        def del_object(name):
            return "Deleted", name, ""

        @staticmethod
        def pass_fail_object(name, diff):
            diff = "Passing"
            if diff is False:
                diff = "Failed"
            return "Changed", name, "{}".format(diff)

        @staticmethod
        def diff_int_object(name, diff):
            if isinstance(diff, float):
                diff = "%.2f" % diff
            else:
                diff = str(diff)
            if not diff.startswith("-"):
                diff = "+"+diff
            return "Changed", name, diff

        @property
        def words_count_as_dict(self):
            return {
                wc.lang: wc.count
                for wc in self.words_count
            }

        @property
        def units_as_dict(self):
            return {
                u.path: u.status
                for u in self.units
            }

    class UnitTest(db.Model):
        """ Units parts of model """
        uuid = db.Column(db.Integer, primary_key=True)
        test_id = db.Column(db.Integer, db.ForeignKey("repo_test.uuid"))
        path = db.Column(db.String(400), nullable=False)
        status = db.Column(db.Boolean, nullable=False)

        def __repr__(self):
            return self.path

    class WordCount(db.Model):
        """ Units parts of model """
        uuid = db.Column(db.Integer, primary_key=True)
        test_id = db.Column(db.Integer, db.ForeignKey("repo_test.uuid"))
        lang = db.Column(db.String(5), nullable=False)
        count = db.Column(db.Integer, nullable=False)

        def __repr__(self):
            return "{}:{}".format(self.lang, self.count)

    return User, Repository, RepoTest, RepoOwnership, UnitTest, WordCount
