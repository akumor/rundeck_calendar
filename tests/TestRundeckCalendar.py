#!/usr/bin/env/python
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
import rundeck_calendar
import unittest
from docker import Client
import json
import requests
import logging


class TestRundeckCalendar(unittest.TestCase):
    """
    Tests functions in the RundeckCalendar class.
    """

    @staticmethod
    def wait_net_service(server, port, timeout=None):
        """ Wait for network service to appear
            :param timeout: in seconds, if None or 0 wait forever
            :return: True of False, if timeout is None may return only True or
                     throw unhandled network exception
        """
        import socket
        import errno

        s = socket.socket()
        if timeout:
            from time import time as now
            # time module is needed to calc timeout shared between two exceptions
            end = now() + timeout

        while True:
            try:
                if timeout:
                    next_timeout = end - now()
                    if next_timeout < 0:
                        return False
                    else:
                        s.settimeout(next_timeout)

                s.connect((server, port))
            except socket.timeout as err:
                # this exception occurs only if timeout is set
                if timeout:
                    return False
            except ConnectionAbortedError:
                pass
            except ConnectionRefusedError:
                pass
            except socket.error as err:
                # catch timeout exception from underlying network library
                # this one is different from socket.timeout
                if type(err.args) != tuple or err != errno.ETIMEDOUT:
                    raise
            else:
                s.close()
                return True

    def setUp(self):
        """
        Prepare to run test.
        """
        global docker_client
        global container
        global api_token
        global session
        log = logging.getLogger('TestRundeckCalendar.setUp')
        docker_client = Client(base_url='unix://var/run/docker.sock')
        for line in docker_client.pull('jordan/rundeck', stream=True):
            print(line.decode('utf-8'))
        log.debug("Creating Rundeck Docker container...")
        container = docker_client.create_container('jordan/rundeck',
                                                   detach=True,
                                                   ports=['4440'],
                                                   environment=['SERVER_URL=http://localhost:4440'],
                                                   host_config=docker_client.create_host_config(port_bindings={
                                                       4440: 4440,
                                                       4443: 4443
                                                   }))
        log.debug("Starting Rundeck Docker container...")
        docker_client.start(container=container.get('Id'))
        log.debug("Waiting for Rundeck service...")
        TestRundeckCalendar.wait_net_service('localhost', 4440, 300)
        log.debug("Waiting to obtain authentication cookie...")
        session = requests.session()
        payload = {'j_username': 'admin', 'j_password': 'admin'}
        while True:
            try:
                resp = session.put('http://localhost:4440/j_security_check', data=payload)
            except requests.exceptions.ConnectionError:
                continue
            else:
                break
            time.sleep(3)

        if resp.status_code == 200:
            # SUCCESS! - now create an API token
            log.debug("Creating an API token...")
            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
            resp2 = session.post('http://localhost:4440/api/11/tokens/admin', headers=headers)
            if resp.status_code == 200:
                # SUCCESS - store the API token
                print(resp2.text)
                try:
                    api_token = json.loads(resp2.text)['id']
                except:
                    docker_client.stop(container=container)
                    docker_client.remove_container(container=container, v=True, link=False, force=True)
                print(api_token)
            else:
                # FAIL!
                docker_client.stop(container=container)
                docker_client.remove_container(container=container, v=True, link=False, force=True)
                raise Exception
        else:
            # FAIL!
            docker_client.stop(container=container)
            docker_client.remove_container(container=container, v=True, link=False, force=True)
            raise Exception

        # create a project
        log.debug("Creating a Rundeck project...")
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        payload = {"name": "TestProject", "config": {}}
        resp = session.post('http://localhost:4440/api/11/projects', headers=headers, data=json.dumps(payload))

        log.debug('Create project API response:\n%s' % resp.text)
        if resp.status_code != 200 and resp.status_code != 201:
            print(resp.text)
            print(resp.status_code)
            raise Exception('Failed to create project "TestProject"')

        # create a job with a schedule
        log.debug("Creating Rundeck job with a schedule...")
        headers = {'Content-type': 'application/xml', 'Accept': 'application/xml'}
        payload = '''
<joblist>
  <job>
    <description></description>
    <dispatch>
      <excludePrecedence>true</excludePrecedence>
      <keepgoing>false</keepgoing>
      <rankOrder>ascending</rankOrder>
      <threadcount>1</threadcount>
    </dispatch>
    <executionEnabled>true</executionEnabled>
    <id>63144201-4c22-4468-92c9-9e56efd530fa</id>
    <loglevel>INFO</loglevel>
    <name>test_job_1</name>
    <nodefilters>
      <filter>localhost</filter>
    </nodefilters>
    <nodesSelectedByDefault>true</nodesSelectedByDefault>
    <schedule>
      <month month='*' />
      <time hour='12' minute='45' seconds='0' />
      <weekday day='2-6' />
      <year year='*' />
    </schedule>
    <scheduleEnabled>true</scheduleEnabled>
    <sequence keepgoing='false' strategy='node-first'>
      <command>
        <exec>echo test_job_1</exec>
      </command>
    </sequence>
    <uuid>63144201-4c22-4468-92c9-9e56efd530fa</uuid>
  </job>
</joblist>
        '''
        params = {'format': 'xml',
                  'dupeOption': 'update',
                  'uuidOption': 'remove'}
        resp = session.post('http://localhost:4440/api/14/project/TestProject/jobs/import', params=params, headers=headers, data=payload)
        log.debug('Create job with schedule API response:\n%s' % resp.text)
        if resp.status_code != 200:
            print(resp.text)
            raise Exception('Failed to import job test_job_1')

        # create a job without a schedule
        log.debug("Creating Rundeck job without a schedule...")
        headers = {'Content-type': 'application/xml', 'Accept': 'application/xml'}
        payload = '''
<joblist>
  <job>
    <description></description>
    <dispatch>
      <excludePrecedence>true</excludePrecedence>
      <keepgoing>false</keepgoing>
      <rankOrder>ascending</rankOrder>
      <threadcount>1</threadcount>
    </dispatch>
    <executionEnabled>true</executionEnabled>
    <id>63144201-4c22-4468-92c9-9e56efd530fa</id>
    <loglevel>INFO</loglevel>
    <name>test_job_2</name>
    <nodefilters>
      <filter>localhost</filter>
    </nodefilters>
    <nodesSelectedByDefault>true</nodesSelectedByDefault>
    <scheduleEnabled>false</scheduleEnabled>
    <sequence keepgoing='false' strategy='node-first'>
      <command>
        <exec>echo test_job_2</exec>
      </command>
    </sequence>
    <uuid>63144201-4c22-4468-92c9-9e56efd530fa</uuid>
  </job>
</joblist>
        '''
        params = {'format': 'xml',
                  'dupeOption': 'update',
                  'uuidOption': 'remove'}
        resp = session.post('http://localhost:4440/api/14/project/TestProject/jobs/import', params=params, headers=headers, data=payload)
        log.debug('Create job without schedule API response:\n%s' % resp.text)
        if resp.status_code != 200:
            print(resp.text)
            raise Exception('Failed to import job test_job_2')

    def tearDown(self):
        """
        Clean up after running test.
        """
        docker_client.stop(container=container)
        docker_client.remove_container(container=container, v=True, link=False, force=True)
        session.close()

    def test_constructor(self):
        """
        Tests the constructor for the RundeckCalendar class.
        """
        rund_cal = rundeck_calendar.RundeckCalendar('localhost', '4440', api_token=api_token, ssl_enabled=False)
        rund_cal.logger.setLevel(logging.DEBUG)
        rund_cal._get_project_names()
        rund_cal._get_rundeck_job_schedules()
        self.assertNotEqual(rund_cal.project_names, [])
        self.assertNotEqual(rund_cal.rundeck_job_schedules, [])

    def test_get_schedule_summary(self):
        """
        Tests the get_schedule_summary method of the RundeckCalendar class.
        """
        log = logging.getLogger("TestRundeckCalendar.test_get_schedule_summary")
        rund_cal = rundeck_calendar.RundeckCalendar('localhost', '4440', api_token=api_token, ssl_enabled=False)
        rund_cal.logger.setLevel(logging.DEBUG)
        correct_output = '''project:job: second minute hour day_of_month month day_of_week year
TestProject:test_job_1: 0 45 12 ? * 2-6 *
'''
        log.debug('Rundeck Calendar Summary:\n' + rund_cal.get_schedule_summary())
        self.assertEqual(rund_cal.get_schedule_summary(), correct_output)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)
    logging.getLogger("TestRundeckCalendar.test_get_schedule_summary").setLevel(logging.DEBUG)
    logging.getLogger("TestRundeckCalendar.test_constructor").setLevel(logging.DEBUG)
    logging.getLogger("TestRundeckCalendar.setUp").setLevel(logging.DEBUG)
    unittest.main()
