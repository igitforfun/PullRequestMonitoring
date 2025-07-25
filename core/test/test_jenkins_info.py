import unittest
import sys, os
import threading
import time, subprocess
try:
    import requests
except ImportError:
    subprocess.run("python -m pip install requests==2.32.3", shell=True, check=True)
    import requests

# Add the parent directory to the system path to import sql_command
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jenkins_info import JenkinsJob
from test_server import test_server

DB_PATH = './core/test/database/test_database.db'
HOST_URL = 'http://localhost:8000'

class TestJenkinsJob(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server = test_server()
        cls.server_thread = threading.Thread(target=cls.server.run_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Give the server a moment to start
        time.sleep(1)

    def setUp(self):
        self.db_path = DB_PATH
        self.jk_gr_jb_url = HOST_URL
        self.ct_job_name = 'CT_job'
        self.ci_job_name = 'CI_job'
        self.test_mode = True
        self.empty_dict = {'pull_request_number': 'None', 'build_id': 'None', 'test_build_number': 'None', 'variant': 'None', 'result': 'None', 'error_type': 'None', 'error_logs': 'None', 'created_at': 'None', 'test_link': 'None', 'artifactory_link': 'None'}
        self.ci_jenkins_job = JenkinsJob(db_path=self.db_path, jk_gr_jb_url=self.jk_gr_jb_url, job_name=self.ci_job_name, test_mode=self.test_mode)
        self.ct_jenkins_job = JenkinsJob(db_path=self.db_path, jk_gr_jb_url=self.jk_gr_jb_url, job_name=self.ct_job_name, test_mode=self.test_mode)

    def test_get_last_build(self):
        last_build = self.ci_jenkins_job.get_last_build()
        self.assertIsInstance(last_build, int)
        self.assertEqual(last_build, 413)

    def test_1_build_error_type(self):
        result_error_type = '<correct error type to be detected'
        result_error_log = '<correct error log to be detected>'
        test_error_type, test_error_log = self.ci_jenkins_job.get_ci_error('1_build_error_type')
        self.assertEqual(test_error_type, result_error_type)
        self.assertEqual(test_error_log, result_error_log)

    def test_2_build_error_type(self):
        result_error_type = '<correct error type to be detected'
        result_error_log = '<correct error log to be detected>'
        test_error_type, test_error_log = self.ci_jenkins_job.get_ci_error('2_build_error_type')
        self.assertEqual(test_error_type, result_error_type)
        self.assertEqual(test_error_log, result_error_log)
    
    # def test_ci_build_xxx(self):
    #     result_error_type = 'xxx'
    #     result_error_log = 'xxx'
    #     test_error_type, test_error_log = self.ci_jenkins_job.get_ci_error('xxx')
    #     print(test_error_type) # To be removed once the string in copied to "result_error_type"
    #     print(test_error_log) # To be removed once the string in copied to "result_error_log"
    #     self.assertEqual(test_error_type, result_error_type)
    #     self.assertEqual(test_error_log, result_error_log)


    def test_get_test_build(self):

        result_dict = {'<dictionary of the correct output>'}
        ct_build_info = self.ct_jenkins_job.get_ct_build_info(self.empty_dict, 'testcases/1_test_error_type')
        self.assertEqual(ct_build_info, result_dict)

        result_dict = {'<dictionary of the correct output>'}
        ct_build_info = self.ct_jenkins_job.get_ct_build_info(self.empty_dict, 'testcases/2_test_error_type')
        self.assertEqual(ct_build_info, result_dict)

        # result_dict = {'xxx':'xxx'}
        # ct_build_info = self.ct_jenkins_job.get_ct_build_info(self.empty_dict, 'xxx')
        # print(ct_build_info) # To be removed once the string is copied to "result_dict"
        # self.assertEqual(ct_build_info, result_dict)

    @classmethod
    def tearDownClass(cls):
        # Stop the server
        cls.server.close_server()
        cls.server_thread.join()

if __name__ == "__main__":
    unittest.main()
