#!/usr/bin/env/python
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
import rundeck_calendar
import unittest


class TestRundeckCalendar(unittest.TestCase):
    """
    Tests the method used to parse the CSV file and update the AppDeploymentListFile object.
    """

    def setUp(self):
        """
        Prepare to run test.
        """
        pass

    def tearDown(self):
        """
        Clean up after running test.
        """
        pass

    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
