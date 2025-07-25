# Description: Test cases for the sql_command module.
# The sql_command module provides a class to interact with a SQLite database.
# The class has methods to create a table, insert data, update data, and close the database connection.
# The test cases cover the creation of a test database and table, inserting data, and updating data.

import unittest
import sqlite3
import os
import sys

# Add the parent directory to the system path to import sql_command
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql_command import sql_command
DB_PATH = ''
table = ''
create_table_SQL = f'''CREATE TABLE IF NOT EXISTS {table} (
                        pull_request_number INTEGER,
                        build_id  INTEGER,
                        test_build_number INTEGER,
                        variant TEXT,
                        result TEXT,
                        error_type TEXT,
                        error_logs TEXT,
                        created_at TEXT,
                        test_link TEXT,
                        artifactory_link TEXT
                    )'''

class TestSqlCommand(unittest.TestCase):

    def setUp(self):
        self.db_path = DB_PATH
        self.sql_cmd = sql_command(self.db_path)
        self.sql_cmd.execute_query(f"DROP TABLE IF EXISTS {table}")
        self.sql_cmd.execute_query(create_table_SQL)

    def tearDown(self):
        """
        Tear down the test case by closing the database connection and removing the test database file.
        """
        self.sql_cmd.close_database()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_insert_and_select(self):
        """
        Test inserting a record into the table and selecting it.
        """
        data = {
            'pull_request_number': 100,
            'ci_build_id': 123,
            'ct_build_number': 2,
            'variant': 'test_variant',
            'result': 'SUCCESS',
            'error_type': 'None',
            'error_logs': 'None',
            'created_at': '2023-10-01 12:00:00',
            'build_link': 'http://example.com/build',
            'artifactory_link': 'http://example.com/artifactory'
        }

        self.sql_cmd.insert_dictionary_to_table(data, table)
        # self.sql_cmd.verify_database(ct_tb)
        row = self.sql_cmd.execute_query_fetchone(f'SELECT * FROM {table} WHERE ct_build_number = 2')
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 100)
        self.assertEqual(row[1], 123)
        self.assertEqual(row[2], 2)
        self.assertEqual(row[3], 'test_variant')
        self.assertEqual(row[4], 'SUCCESS')
        self.assertEqual(row[5], 'None')
        self.assertEqual(row[6], 'None')
        self.assertEqual(row[7], '2023-10-01 12:00:00')
        self.assertEqual(row[8], 'http://example.com/build')
        self.assertEqual(row[9], 'http://example.com/artifactory')

        """
        Test updating a record in the table.
        """
        update_dict = {
            'ct_build_number': 2,
            'ci_build_id': 124,
            'variant': 'test_variant',
            'result': 'SUCCESS',
            'error_type': 'None',
            'created_at': '2023-10-01 12:00:00',
            'build_link': 'http://example.com/build_v1',
            'artifactory_link': 'http://example.com/artifactory'
        }
        self.sql_cmd.execute_update_command(update_dict, table, 'ct_build_number')
        row = self.sql_cmd.execute_query_fetchone(f"SELECT * FROM {table} WHERE ct_build_number = 2")
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 100)
        self.assertEqual(row[1], 124)
        self.assertEqual(row[2], 2)
        self.assertEqual(row[3], 'test_variant')
        self.assertEqual(row[4], 'SUCCESS')
        self.assertEqual(row[5], 'None')
        self.assertEqual(row[6], 'None')
        self.assertEqual(row[7], '2023-10-01 12:00:00')
        self.assertEqual(row[8], 'http://example.com/build_v1')
        self.assertEqual(row[9], 'http://example.com/artifactory')

    def test_create_dictionary_from_table(self):
        """
        Test creating a dictionary from the table.
        """
        expected_dict = {
            "pull_request_number": 'None',
            "ci_build_id": 'None',
            "ct_build_number": 'None',
            'variant': 'None',
            'result': 'None',
            'error_type': 'None',
            'error_logs': 'None',
            'created_at': 'None',
            'build_link': 'None',
            'artifactory_link': 'None'
        }
        result_dict = self.sql_cmd.create_dictionary_from_table(table)
        self.assertEqual(result_dict, expected_dict)

    def test_get_max_build_number(self):
        """
        Test getting the maximum build number from the table.
        """
        self.sql_cmd.execute_query(f"INSERT INTO {table} VALUES (100, 123, 1, 'test_variant', 'SUCCESS', 'None', 'None', '2023-10-01 12:00:00', 'http://example.com/build', 'http://example.com/artifactory')")
        self.sql_cmd.execute_query(f"INSERT INTO {table} VALUES (100, 124, 2, 'test_variant', 'SUCCESS', 'None', 'None', '2023-10-01 12:00:00', 'http://example.com/build', 'http://example.com/artifactory')")
        self.sql_cmd.execute_query(f"INSERT INTO {table} VALUES (100, 124, 1, 'test_variant_1', 'SUCCESS', 'None', 'None', '2023-10-01 12:00:00', 'http://example.com/build', 'http://example.com/artifactory')")
        max_build_number = self.sql_cmd.get_max_build_number(table, column_name='ct_build_number',column_variant='variant', variant='test_variant')
        self.assertEqual(max_build_number, 2)
        max_build_number = self.sql_cmd.get_max_build_number(table, column_name='ct_build_number',column_variant='variant', variant='test_variant_1')
        self.assertEqual(max_build_number, 1)

if __name__ == '__main__':
    unittest.main()
