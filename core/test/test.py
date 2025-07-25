import unittest

def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test files to the suite
    print('Running test of Jenkins_info.py')
    suite.addTests(loader.discover('core/test', pattern='test_jenkins_info.py'))
    print('Running test of sql_command.py')
    suite.addTests(loader.discover('core/test', pattern='test_sql_command.py'))
    print('Running test of info_from_url.py')
    suite.addTests(loader.discover('core/test', pattern='test_info_from_url.py'))
  

    runner = unittest.TextTestRunner()
    result = runner.run(suite)

    if result.wasSuccessful():
        print("All tests passed!")
    else:
        print("Some tests failed.")

if __name__ == '__main__':
    run_tests()