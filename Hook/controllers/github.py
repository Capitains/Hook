from Hook.app import github_api, app
from flask import url_for


def Repository(repository):
    """ Avoids import of Hook.models.github by returning the right class

    :param repository: Repository object
    :type repository: Hook.models.github.repository
    :return:
    :rtype: class
    """
    if hasattr(repository, "repository"):
        return repository.repository.__class__
    else:
        return repository.__class__


def git_status(repository_test, state="pending"):
    """ Add the status of a Repository test to github

    :param repository_test: Repository Test object
    :type repository_test: Hook.models.github.RepoTest
    :param state: Status string
    :type state: str
    :return:
    :rtype: bool
    """
    with app.app_context():
        uri = "repos/{owner}/{repo}/statuses/{sha}".format(owner=repository_test.username, repo=repository_test.reponame, sha=repository_test.sha)
        if state is not None:
            state = "error"
            sentence = "Test cancelled"
        elif repository_test.status is True:
            state = "success"
            sentence = "Full repository is cts compliant"
        elif repository_test.status is False:
            state = "failure"
            sentence = "{0} of unit tests passed".format(repository_test.coverage)
        else:
            state = "pending"
            sentence = "Currently testing..."

        data = {
          "state": state,
          "target_url": "http://" + "/".join([s for s in [app.config["SERVER_NAME"], app.config["APPLICATION_ROOT"]]]) + "/repo/{username}/{reponame}/{uuid}".format(username=repository_test.username, reponame=repository_test.reponame, uuid=repository_test.uuid),
          "description": sentence,
          "context": "continuous-integration/capitains-hook"
        }

        params = {}
        if hasattr(g, "user") is not True:
            full_repository = Repository(repository_test).objects.get(owner__iexact=repository_test.username, name__iexact=repository_test.reponame)
            user = full_repository.authors[0]
            access_token = user.github_access_token
            params = {"access_token": access_token}

        github_api.post(uri, data=data, params=params)
    return True


def fetch(user):
    """ Fetch repositories information of a user

    :param user: Repository we want information about
    :type user: Hook.models.github.Repository

    :returns: List of Repositories
    :rtype: [Hook.models.github.Repository]
    """
    response = []
    if hasattr(g, "user") and g.user == user:
        # We clear the old authors
        user.remove_authorship()

        repositories = github_api.get(
            "user/repos",
            params={
                "affiliation": "owner,collaborator,organization_member",
                "access_token": user.github_access_token
            },
            all_pages=True
        )

        for repo in repositories:
            owner = repo["owner"]["login"]
            name = repo["name"]

            response.append(user.addto(owner=owner, name=name))
    return response
