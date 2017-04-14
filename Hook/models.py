__author__ = 'Thibault Clerice'

import datetime
import re
import random
import hashlib

from tabulate import tabulate
from Hook.exceptions import *
from collections import defaultdict
from math import isclose
from operator import itemgetter
from flask_login import UserMixin
from werkzeug.exceptions import NotFound


pr_finder = re.compile("pull\/([0-9]+)\/head")


def make_travis_env():
    by = hashlib.sha1(str(random.getrandbits(128)).encode()).hexdigest()
    return by


def model_maker(db, prefix=""):
    """ Creates model based on Database connection

    :param db: Flask SQLAlchemy Database instance
    :type db: flask_sqlalchemy.SQLAlchemy
    :return: Models
    """

    RepoOwnership = db.Table("repoownership",
        db.Column('user_uuid', db.Integer, db.ForeignKey('user.uuid')),
        db.Column('repo_uuid', db.Integer, db.ForeignKey('repository.uuid')),
        #db.UniqueConstraint('user_uuid', 'repo_uuid', name='unique_repo_link')
    )

    class User(UserMixin, db.Model):
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
        uuid = db.Column(db.Integer, primary_key=True, autoincrement=True)
        email = db.Column(db.String(255), unique=True, nullable=True)
        login = db.Column(db.String(255), unique=True, nullable=False)
        git_id = db.Column(db.String(255))
        github_access_token = db.Column(db.String(200), nullable=False)
        avatar = db.Column(db.String(2000), nullable=True)
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

        def get_id(self):
            """ (LoginManager) This method must return a unicode that uniquely identifies this user, and can be used to\
            load the user from the user_loader callback. Note that this must be a unicode - if the ID is natively an \
            int or some other type, you will need to convert it to unicode.

            :return: UUID
            :rtype: str
            """
            return str(self.uuid)

        def remove_authorship(self, _commit=True):
            for repo in self.repositories:
                self.repositories.remove(repo)
            if _commit is True:
                db.session.commit()

        def __repr__(self):
            return self.login

    class Repository(db.Model):
        """ Just as a cache of available repositories for user """
        uuid = db.Column(db.Integer, primary_key=True, autoincrement=True)
        owner = db.Column(db.String(200), nullable=False)
        name = db.Column(db.String(200), nullable=False)
        active = db.Column(db.Boolean, nullable=False, default=False)
        main_branch = db.Column(db.String(200), nullable=False, default="master")
        travis_env = db.Column(db.String(200), default=make_travis_env)

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
                filter(RepoTest.source == self.main_branch).\
                order_by(RepoTest.run_at.desc()).\
                first()

        def get_test(self, uuid):
            return self.tests.\
                filter(RepoTest.uuid == uuid).\
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
        def get_or_raise(owner, name):
            """ Finds a repository by owner and name

            :param owner: Name of the repo owner
            :param name: Name of the repository
            :return:
            """
            query = Repository.query.filter_by(owner=owner, name=name).first()
            if query is None:
                raise NotFound(description="Unknown Repository")
            return query

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

        def regenerate_travis_env(self, user, session=None):
            """ Regenerate the Travis Env

            :param user: User to check rights for
            :param session: Session to commit with
            :return:
            """
            if self.has_rights(user):
                self.travis_env = make_travis_env()
                if session:
                    session.commit()
                return True
            else:
                raise RightsException("Not enough rights")

        def register_test(
                self, source, travis_uri, travis_build_id, user, avatar, texts_total,
                texts_passing, metadata_total, metadata_passing, coverage, nodes_count,
                units, words_count=None, sha=None, comment_uri=None, _get_diff=True, event_type="push"
        ):
            """ Save a test and produce a diff if this is master

            :param source: Source should be the Pull Request Number or the branch
            :type source: Str
            :param travis_uri: travis_uri
            :type travis_uri: Str
            :param travis_build_id: travis_build_id
            :type travis_build_id: Str
            :param user: Login of the agent
            :type user: str
            :param avatar: Avatar of the user
            :type avatar: Str
            :param texts_total: texts_total
            :type texts_total: Int
            :param texts_passing: texts_passing
            :type texts_passing: Int
            :param metadata_total: metadata_total
            :type metadata_total: Int
            :param metadata_passing: metadata_passing
            :type metadata_passing: int
            :param coverage: Coverage of
            :type coverage: float
            :param nodes_count: nodes_count
            :type nodes_count: int
            :param units: Dictionary Path->Status
            :type units: dict
            :param words_count: Dictionary LanguageCode -> Number of words
            :type words_count: dict
            :param comment_uri: URL Address of the comment
            :type comment_uri: str
            :param sha: SHA of the commit
            :type sha: str
            :param event_type: Type of the event
            :type event_type: str
            :return:
            """
            last_master = self.last_master_test
            repo = RepoTest(
                repository=self.uuid, source=source, travis_uri=travis_uri,
                travis_build_id=travis_build_id, user=user, avatar=avatar,
                texts_total=texts_total, texts_passing=texts_passing, metadata_total=metadata_total,
                metadata_passing=metadata_passing, coverage=coverage, nodes_count=nodes_count,
                sha=sha, comment_uri=comment_uri, event_type=event_type
            )
            diff = None
            if last_master is not None and _get_diff is True:
                diff = repo.diff(self.last_master_test, units, words_count)

            db.session.add(repo)
            db.session.commit()

            if words_count is not None:
                repo.save_words_count(words_count)

            if self.main_branch == source:
                repo.save_units(units, _commit=True, _last_master=last_master)

            return repo, diff

    class RepoTest(db.Model):
        """ Complete repository status """
        uuid = db.Column(db.Integer, primary_key=True, autoincrement=True)
        repository = db.Column(db.Integer, db.ForeignKey('repository.uuid'), nullable=False)

        run_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

        """ Source should be the Pull Request Number or the branch
        """
        source = db.Column(db.String(250), nullable=None)
        sha = db.Column(db.String(64), nullable=True)

        travis_uri = db.Column(db.String(2000), nullable=False)
        travis_build_id = db.Column(db.String(10), nullable=False)
        user = db.Column(db.String(200), nullable=False)
        avatar = db.Column(db.String(2000), nullable=False)

        comment_uri = db.Column(db.String(2000), nullable=True)
        event_type = db.Column(db.String(12), nullable=False, default="push")

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
        repository_dyn = db.relationship(
            "Repository",
            backref=db.backref('repo')
        )

        dyn_units = db.relationship(
            "UnitTest",
            backref=db.backref('unit_test_dyn'), lazy="dynamic",
        )
        dyn_words = db.relationship(
            "WordCount",
            backref=db.backref('word_count_dyn'), lazy="dynamic"
        )

        @property
        def status(self):
            if self.coverage > 90.0:
                return "success"
            elif self.coverage > 75.0:
                return "acceptable"
            else:
                return "failed"

        def __repr__(self):
            return self.travis_build_id

        def save_units(self, unit_dict, _last_master=None, _force_clear=True, _commit=True):
            """ Save a dictionary of units in the database

            :param unit_dict:
            :type unit_dict:
            :param _force_clear: Force removal of former scores
            :param _commit: Automatically commit
            :return:
            """
            if _force_clear:
                if _last_master is not None:
                    _last_master.dyn_units.delete()
            for path, status in unit_dict.items():
                u = UnitTest(path=path, status=status)
                self.units.append(u)
            if _commit is True:
                db.session.commit()

        def save_words_count(self, words_count, _last_master=None, _force_clear=True, _commit=True):
            """ Save a dictionary of units in the database

            :param words_count: Key-value pairs of lang code + word count
            :param _commit: Automatically commit
            :return:
            """
            if _force_clear and _last_master is not None:
                _last_master.dyn_words.delete()
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
                (self.diff_dict, last_master.diff_dict, "Global"),
                (units, last_master.units_as_dict, "Units")
            ]
            if words_count is not None:
                items.append((words_count, last_master.words_count_as_dict, "Words"))
            ret = {}
            for me, you, name in items:
                current = defaultdict(list)
                complete_keys = set(list(me.keys()) + list(you.keys()))
                for key in complete_keys:
                    if key not in you:
                        current["New"].append(self.new_object(key))
                        if isinstance(me[key], bool):
                            current["Changed"].append(self.pass_fail_object(key, me[key]))
                    elif key not in me:
                        current["Deleted"].append(self.del_object(key))
                    elif me[key] != you[key]:
                        if isinstance(me[key], bool):
                            current["Changed"].append(self.pass_fail_object(key, me[key]))
                        elif isinstance(me[key], float):
                            if not isclose(me[key], you[key], rel_tol=0.0001):
                                current["Changed"].append(self.diff_int_object(key, me[key] - you[key]))
                        else:
                            current["Changed"].append(self.diff_int_object(key, me[key]-you[key]))
                for key, val in current.items():
                    current[key] = sorted(val, key=itemgetter(0))
                ret[name] = current
            return ret

        @staticmethod
        def table(diff_dict, mode="md"):
            """ Takes a diff dict and creates a table from it

            :param diff_dict: Diff dict from self.diff
            :param mode: md or html given the wished output
            :return: Table as string
            """
            if mode == "md":
                mode = "pipe"
            output = []
            keys = ["Global", "Units"]
            if "Words" in diff_dict:
                keys = ["Global", "Words", "Units"]
            for name in keys:
                table = diff_dict[name]
                if len(table["New"] + table["Deleted"] + table["Changed"]) > 0:
                    output.append("## %s" % name)
                    output.append(
                        tabulate(
                            [["`"+item+"`", value] for item, value in sorted((table["New"] + table["Deleted"]), key=itemgetter(0))] + \
                            [["`"+item+"`", value] for item, value in sorted(table["Changed"], key=itemgetter(0))],
                            ["Changed", "Status"],
                            tablefmt=mode
                        )
                    )
            return "\n\n".join(output)

        @property
        def diff_dict(self):
            return {
                "texts_total": self.texts_total,
                "texts_passing": self.texts_passing,
                "metadata_total": self.metadata_total,
                "metadata_passing": self.metadata_passing,
                "coverage": self.coverage,
                "nodes_count": self.nodes_count
            }

        @property
        def dict(self):
            dct = self.diff_dict
            if self.words_count is not None:
                dct["words_count"] = self.words_count_as_dict

            if self.comment_uri is not None:
                dct["comment_uri"] = self.comment_uri
            return dct

        @staticmethod
        def new_object(name):
            return name, "New"

        @staticmethod
        def del_object(name):
            return name, "Deleted"

        @staticmethod
        def pass_fail_object(name, diff):
            text_diff = "Passing"
            if diff is False:
                text_diff = "Failing"
            return name, text_diff

        @staticmethod
        def diff_int_object(name, diff):
            if isinstance(diff, float):
                diff = "%.2f" % diff
            else:
                diff = str(diff)
            if not diff.startswith("-"):
                diff = "+"+diff
            return name, diff

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
        uuid = db.Column(db.Integer, primary_key=True, autoincrement=True)
        test_id = db.Column(db.Integer, db.ForeignKey("repo_test.uuid"))
        path = db.Column(db.String(400), nullable=False)
        status = db.Column(db.Boolean, nullable=False)

        def __repr__(self):
            return self.path

    class WordCount(db.Model):
        """ Units parts of model """
        uuid = db.Column(db.Integer, primary_key=True, autoincrement=True)
        test_id = db.Column(db.Integer, db.ForeignKey("repo_test.uuid"))
        lang = db.Column(db.String(5), nullable=False)
        count = db.Column(db.Integer, nullable=False)

        def __repr__(self):
            return "{}:{}".format(self.lang, self.count)

    class Models(object):
        def __init__(self):
            self.User = User
            self.Repository = Repository
            self.RepoTest = RepoTest
            self.RepoOwnership = RepoOwnership
            self.UnitTest = UnitTest
            self.WordCount = WordCount

    return Models()
