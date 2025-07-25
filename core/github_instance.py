from github import Github
from github import Auth

class GithubInstance:
    def __init__(self, token, base_url):
        self.auth =  Auth.Token(token)
        self.base_url = base_url
        self.gh = Github(auth=self.auth, base_url=self.base_url)

    def get_authenticated_user(self):
        return self.gh.get_user().login
    
    def get_all_pull_requests(self, repository_name, branch, state='open'):
        repo = self.gh.get_repo(f"{repository_name}")
        if branch:
            return repo.get_pulls(state=state, base=branch)
        else:
            return repo.get_pulls(state=state)
    
    def get_single_pull_request(self, repository_name, number):
        repo = self.gh.get_repo(f"{repository_name}")
        return repo.get_pull(number)
    
