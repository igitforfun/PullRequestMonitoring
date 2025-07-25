import json, os

# Path to the JSON configuration file
JSON_PATH = os.path.join(os.path.dirname(__file__)+'\..\config.json')

class ConfigInfo:
    """
    A class to handle configuration information from a JSON file.
    """

    def __init__(self, json_path=JSON_PATH, dashboard_conf='Jenkins_Dashboard_Config'):
        """
        Initialize the ConfigInfo object.

        :param json_path: Path to the JSON configuration file.
        """
        self.json_path = json_path
        self.dashboard_conf=dashboard_conf
        self.json_data = self.load_json()
        self.index = 0
        self.type = ''

    def get_index(self):
        """
        Get the index of the configuration based on the project type.

        :return: Index of the configuration.
        :raises ValueError: If the type is not found in the configuration.
        """
        for index, project in enumerate(self.json_data['config']):
            if project['type'] == self.type:
                return index
        raise ValueError(f"Jenkins/Github type '{self.type_jenkins}' not found in configuration.")
    
    def switch_project_type(self, type):
        """
        returns the index based on the input that can be
        found in config.json

        """
        self.type = type
        self.index = self.get_index()

    def load_json(self):
        """
        Load the JSON configuration file.

        :return: Parsed JSON data.
        """
        try:
            with open(self.json_path) as f:
                data = json.load(f)
            json_data = data[self.dashboard_conf]
            return json_data
        except Exception as e:
            raise KeyError(f"{e}")
        
    def get_port(self):
        """
        Get the port number from the configuration.

        :return: Port number.
        """
        return self.json_data['port']
    
    def get_ip_address(self):
        """
        Get IP address of the server that is hosting the application
        """
        return self.json_data['ip_address']
    
    def get_jenkins_group_job_url(self):
        """
        Get the Jenkins group job URL from the configuration.

        :return: Jenkins group job URL.
        """
        return self.json_data['config'][self.index]['jenkins_group_job_url']

    def get_job_names(self):
        """
        Get the list of Jenkins job names from the configuration.

        :return: List of Jenkins job names.
        """
        return self.json_data['config'][self.index]['jenkins_jobs']
    
    def get_ct_jobs_regex(self):
        """
        Get the regex string for the triggered test jobs for a Jenkins build job

        :return: Regex string
        """
        return self.json_data['config'][self.index]['jenkins_test_jobs_regex']
    
    def get_table(self):
        """
        Get the table name from the configuration.

        :return: table name to be created in database.
        """
        return self.json_data['config'][self.index]['database_table']
    
    def get_meta_pr_db_table(self):
        """
        Get the meta pull request table name from the configuration.

        :return: table name to be created in database.
        """
        return self.json_data['config'][self.index]['meta_pr_database_table']
    
    def get_sub_pr_db_table(self):
        """
        Get the sub pull request table name from the configuration.

        :return: table name to be created in database.
        """
        return self.json_data['config'][self.index]['sub_pr_database_table']
    
    def get_github_target_branch(self):
        """
        Get the target branch where the pull request is created to merge into

        :return: github target branch
        """
        return self.json_data['config'][self.index]['target_branch']
    
    def get_pull_requests_active_period(self):
        """
        Get the predefined active time frame of pull requests in days

        :return: period in days
        """
        return self.json_data['pull_request_active_period']

    def get_github_server(self):
        """
        Get the github server

        :return: github server link
        """
        return self.json_data['config'][self.index]['github_server']
    
    def get_github_meta_repo(self):
        """
        Get the github meta repository
        :return: github repository
        """
        return self.json_data['config'][self.index]['github_meta_repository']
    
    def get_github_organization(self):
        """
        Get the github organization where the repositories are stored at
        :return: github organization
        """
        return self.json_data['config'][self.index]['github_organization']
    
    def get_labels_list(self):
        """
        Get the list of labels to monitor for PR's jenkins job trigger
        """
        return self.json_data['labels']
    

if __name__ == '__main__':
    # Example usage of the ConfigInfo class
    js = ConfigInfo()
