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
        docker_client = Client(base_url='unix://var/run/docker.sock')
        for line in docker_client.pull('jordan/rundeck', stream=True):
            print(line.decode('utf-8'))
        container = docker_client.create_container('jordan/rundeck',
                                                   detach=True,
                                                   ports=['4440'],
                                                   environment=['SERVER_URL=http://localhost:4440'],
                                                   host_config=docker_client.create_host_config(port_bindings={
                                                       4440: 4440,
                                                       4443: 4443
                                                   }))
        docker_client.start(container=container.get('Id'))
        TestRundeckCalendar.wait_net_service('localhost', 4440, 300)
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

    def tearDown(self):
        """
        Clean up after running test.
        """
        docker_client.stop(container=container)
        docker_client.remove_container(container=container, v=True, link=False, force=True)

    def test_constructor(self):
        rund_cal = rundeck_calendar.RundeckCalendar('localhost', '4440', api_token=api_token, ssl_enabled=False)
        self.assertEquals(rund_cal.project_names, [])
        self.assertEquals(rund_cal.rundeck_job_schedules, [])
        # TODO create a project and some test jobs with and without schedules

if __name__ == '__main__':
    unittest.main()
