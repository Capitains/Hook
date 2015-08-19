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


def hook(repository):
    """ Create or delete hooks on GitHub API

    :param repository: Repository to add or delete the hook from
    :type repository: Hook.models.github.Repository

    :returns: Active status
    """
    uri = "repos/{owner}/{repo}/hooks".format(owner=repository.owner, repo=repository.name)
    payload = app.config["DOMAIN"] + url_for("api_test_payload")

    if repository.tested is True:
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
        service = github_api.post(uri, data=hook_data)
        if "id" in service:
            repository.update(hook_id=service["id"])
    else:
        if repository.hook_id is None:
            hooks = github_api.get(uri)
            hooks = [service for service in hooks if service["config"]["url"] == payload]
            if len(hooks) == 0:
                uuid = None
            else:
                uuid = hooks[0]["id"]
        else:
            uuid = repository.hook_id
        if uuid is not None:
            github_api.delete("repos/{owner}/{repo}/hooks/{id}".format(owner=repository.owner, repo=repository.name, id=uuid))

    return repository.tested


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
        user.clean()

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
