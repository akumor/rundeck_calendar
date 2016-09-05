#!/usr/bin/env/python
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
import rundeck_calendar
import unittest
from docker import Client
import json
import requests

class TestRundeckCalendar(unittest.TestCase):
    """
    Tests the method used to parse the CSV file and update the AppDeploymentListFile object.
    """

    def setUp(self):
        """
        Prepare to run test.
        """
        global docker_client
        global container
        docker_client = Client(base_url='unix://var/run/docker.sock')
        for line in docker_client.pull('jordan/rundeck', stream=True):
            print(line.decode('utf-8'))
        container = docker_client.create_container('jordan/rundeck',
                                                   detach=True,
                                                   ports=['4440'],
                                                   environment=['SERVER_URL=http://localhost:4440'])
        docker_client.start(container=container.get('Id'))
        resp = requests
        # TODO use requests library with the admin/admin account to generate a cookie that can be used for API requests

    def tearDown(self):
        """
        Clean up after running test.
        """
        pass

    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
