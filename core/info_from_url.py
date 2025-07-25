import urllib.request
import re
from logging_config import logger
import html

JENKIN_SER_URL = ""
JENKIN_JOB_NAME = ""
JENKIN_URL = JENKIN_SER_URL + JENKIN_JOB_NAME
RE_PATTERN = r'{}(\d*?)/'.format(JENKIN_JOB_NAME)

"""
The class InfoFromUrl is used to extract the information from the URL.
The URL is the Jenkins server or GitHub.
The pattern is the pattern that you want to extract from the URL.
"""

class InfoFromUrl:
    def __init__(self, url, pattern):
        """
        Initialize with URL and pattern.
        
        :param url: URL of the Jenkins server or GitHub
        :param pattern: Pattern to extract the information from the URL
        """
        self.url = url
        self.pattern = pattern
        self.url_content = self.fetch_content()

    def fetch_content(self):
        """
        Get the content of the URL.
        
        :return: Content of the URL as a string
        """
        try:
            with urllib.request.urlopen(self.url) as f:
                self.url_content = f.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error: URL {self.url} is not valid. Please check. Exception: {e}")
            return ""
        # print(self.url_content,  file=open('log.txt', 'w', encoding='utf-8'))
        return self.url_content

    def extract_info_from_url(self, pattern=None, dotall=False):
        """
        Extract information from the URL based on the pattern.
        
        :param pattern: Optional pattern to override the existing pattern
        :return: List of strings that match the pattern
        """
        if pattern:
            self.pattern = pattern

        if dotall:
            res = re.findall(self.pattern, self.url_content, re.DOTALL)
        else:
            res = re.findall(self.pattern, self.url_content)
        return res

if __name__ == '__main__':
    info = InfoFromUrl(JENKIN_URL, RE_PATTERN)
    # print(info.extract_info_from_url())