# This file is used to test the InfoFromUrl class in the info_from_url.py file.
# The InfoFromUrl class is used to extract the information from the URL.
import unittest,sys,os

# Add the parent directory to the system path to import sql_command
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 

from info_from_url import InfoFromUrl


JENKIN_SER_URL = ""
JENKIN_JOB_NAME = ""
JENKIN_URL = JENKIN_SER_URL + JENKIN_JOB_NAME
RE_PATTERN = r'{}(\d*?)/'.format(JENKIN_JOB_NAME)

class TestInfoFromUrl(unittest.TestCase):
    def setUp(self):
        """
        Set up the test case with URL and pattern.
        """
        self.url = JENKIN_URL
        self.pattern = RE_PATTERN
        self.info = InfoFromUrl(self.url, self.pattern)

    def test_get_url_content(self):
        """
        Test the get_url_content method.
        """
        content = self.info.fetch_content()
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)

    def test_extract_info_from_url(self):
        """
        Test the extract_info_from_url method.
        """
        result = self.info.extract_info_from_url()
        self.assertIsInstance(result, list)
        for item in result:
            self.assertTrue(item.isdigit())

if __name__ == '__main__':
    unittest.main()