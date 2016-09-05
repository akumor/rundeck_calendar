#!/usr/bin/env python
"""

"""
# TODO add Google Calendar output https://github.com/fabriceb/gcalcron
import os
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
import sys
import requests
import json
import lxml.etree as etree
import getopt
import configparser
import signal


class RundeckCalendar:
    """
    Class used to produce different representations of Rundeck job schedule data.
    """

    class RundeckJobSchedule:
        """
        Class used to store data about Rundeck jobs related to their schedule.
        """

        def __init__(self, uuid, name, project, cron_schedule=None, second=None, minute=None, hour=None,
                     day_of_month=None, month=None, day_of_week=None, year=None):
            """
            :param uuid: UUID of the Rundeck job
            :param name: Name of the Rundeck job
            :param project: Project that the Rundeck job belongs to
            :param cron_schedule: Schedule for the Rundeck job
            :param second: second(s) at which the job is scheduled
            :param minute: minute(s) at which the job is scheduled
            :param hour: hour(s) at which the job is scheduled
            :param day_of_month: day of the month on which the job is scheduled
            :param month: month(s) on which the job is scheduled
            :param day_of_week: day of week on which the job is scheduled
            :param year: year on which the job is scheduled
            :return: RundeckJobSchedule object
            """
            self.logger = logging.getLogger(__name__)
            self.uuid = uuid
            self.name = name
            self.project = project
            if cron_schedule is None:
                self.second = second if second is not None else '?'
                self.minute = minute if minute is not None else '?'
                self.hour = hour if hour is not None else '?'
                self.day_of_month = day_of_month if day_of_month is not None else '?'
                self.month = month if month is not None else '?'
                self.day_of_week = day_of_week if day_of_week is not None else '?'
                self.year = year if year is not None else '?'
            else:
                cron_sched_split = cron_schedule.split(' ')
                if len(cron_sched_split) != 7:
                    self.logger.debug(
                        'Invalid string supplied for cron_schedule to the RundeckJobSchedule class: %s' % cron_schedule)
                    raise Exception
                self.second = cron_sched_split[0]
                self.minute = cron_sched_split[1]
                self.hour = cron_sched_split[2]
                self.day_of_month = cron_sched_split[3]
                self.month = cron_sched_split[4]
                self.day_of_week = cron_sched_split[5]
                self.year = cron_sched_split[6]

    class RUNDECKAPIError(Exception):
        """
        Exception for errors that occur while execution against the Rundeck API.
        """

        def __init__(self, status_code=None, response=None):
            """
            Store information for this exception.
            :param status_code: integer representing the HTTP status code from the API call
            :param response: string from the HTTP response
            :return: RUNDECKAPIError object
            """
            self.status_code = status_code
            self.response = response

        def __str__(self):
            """
            Returns string representation of this exception
            :return: string
            """
            return repr((self.status_code, self.response))

    def __init__(self, host, port, api_token, ssl_enabled=True):
        """
        Returns a RundeckCalendar object to represent the schedules of jobs on the Rundeck server
        :param host: FQDN or IP address of the Rundeck server
        :param port: port on which the Rundeck service is listening
        :param api_token: string containing a token used to authenticate with the Rundeck API.
        :param ssl_enabled: True if SSL should be used to establish connection with the Rundeck server and False otherwise.
        :return: RundeckCalendar object
        """
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.api_token = api_token
        self.ssl_enabled = ssl_enabled
        self.project_names = self._get_project_names()
        self.rundeck_jobs = self._get_rundeck_jobs()

    def _get_project_names(self):
        """
        Returns list of all the project names.
        :return: list of Rundeck project names
        """
        if self.ssl_enabled:
            execution_url = 'https://'
        else:
            execution_url = 'http://'
        execution_url += self.host + ':' + self.port + '/api/1/projects'
        headers = {'Content-Type': 'application/json', 'X-RunDeck-Auth-Token': self.api_token}
        resp = requests.get(execution_url, headers=headers, verify=False)
        if resp.status_code not in (204, 200):
            self.logger.error("Failed to obtain list of projects from the API.")
            raise self.RUNDECKAPIError(status_code=resp.status_code, response=resp.text)
        else:
            doc = etree.fromstring(resp.text)
            # print resp.text
            project_names = []
            for projects in doc:
                for name in projects.findall('project'):
                    project_names.append(name.find('name').text)
            return project_names

    def _get_rundeck_job_schedules(self):
        """
        Issues requests to the Rundeck API to obtain information regarding scheduled jobs.
        :return: a list of RundeckJobSchedule objects
        """
        rundeck_job_schedules = []
        for project_name in self.project_names:
            if self.ssl_enabled:
                execution_url = 'https://'
            else:
                execution_url = 'http://'
            execution_url += self.host + ':' + self.port + '/api/14/project/%s/jobs/export' % project_name
            headers = {'Content-Type': 'application/xml', 'X-RunDeck-Auth-Token': self.api_token}
            resp = requests.get(execution_url, headers=headers, verify=False)
            if resp.status_code not in (204, 200):
                self.logger.error("Failed to obtain job information from the API for %s project." % project_name)
                raise self.RUNDECKAPIError(status_code=resp.status_code, response=resp.text)
            else:
                # Parse the XML
                doc = etree.fromstring(resp.text)
                # Iterate over jobs listed in the XML
                for job in doc.findall('job'):
                    # Only bother with the jobs that have schedules
                    if job.find('scheduleEnabled') is not None:
                        if job.find('scheduleEnabled').text == 'false':
                            continue
                    if job.find('schedule') is not None:
                        sched = job.find('schedule')
                        # Store schedule data
                        if sched.attrib['crontab'] is not None:
                            rundeck_job_schedule = self.RundeckJobSchedule(job.find('id').text,
                                                                           job.find('name').text,
                                                                           project_name)
                            try:
                                rundeck_job_schedule.cron_schedule = sched.attrib['crontab']
                            except (AttributeError, KeyError) as e:
                                pass
                        else:
                            rundeck_job_schedule = self.RundeckJobSchedule(job.find('id').text,
                                                                           job.find('name').text,
                                                                           project_name)
                            try:
                                rundeck_job_schedule.second = sched.find('time').attrib['seconds']
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.minute = sched.find('time').attrib['minutes']
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.hour = sched.find('time').attrib['hour']
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.day_of_month = '?'
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.month = sched.find('month').attrib['month']
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.day_of_week = sched.find('weekday').attrib['day']
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.year = sched.find('year').attrib['year']
                            except (AttributeError, KeyError) as e:
                                pass
                            if sched.find('month').attrib['day'] is not None:
                                try:
                                    rundeck_job_schedule.day_of_month = sched.find('month').attrib['day']
                                except KeyError:
                                    pass

                        rundeck_job_schedules.append(rundeck_job_schedule)
        return rundeck_job_schedules

# Setup logging
LOGGER_NAME = 'disable_rundeck_job'
LOGGER = logging.getLogger(LOGGER_NAME)
LOGGER.setLevel(logging.INFO)
# create console handler with a higher log level
CONSOLE_HANDLER = logging.StreamHandler(sys.stdout)
CONSOLE_HANDLER.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')
CONSOLE_HANDLER.setFormatter(formatter)
# add the handlers to the logger
LOGGER.addHandler(CONSOLE_HANDLER)


# Dictionary containing cli argument names (keys) and their values
ARG_VALUES = {"server=": "",
              "port=": "",
              "apitoken=": "",
              "credentials=": "",
              "logfilepath=": ""
              }

def signal_handler(signal, frame):
    """
    Handles signals such as SIGINT.
    :param signal: signal number
    :param frame: current stack frame
    """
    # Print Ctrl+C message and exit
    LOGGER.info('You pressed Ctrl+C! Script Exited.')
    sys.exit(0)

def process_args():
    """
    Handles the parsing of command line arguments to the script and modifies global variable ARG_VALUES accordingly.
    """
    global LOGGER
    global CONSOLE_HANDLER
    help_string = '''
Usage:

    rundeck_calendar.py [options]

    -h or
    --help                                   Prints this help menu.

    -s <FQDN or IP> or                       Fully qualified domain name or IP address of the Rundeck server where the
    --server=<FQDN or IP>                    job will be executed.

    -p <port> or
    --port=<port>                            Port to connect to on the Rundeck server in order to access the REST API.

    -a <api token> or                        API token to use to connect to the Rundeck REST API.
    --apitoken=<api token>                   NOTE: Not valid with the --credentials option.

    -c <path to credentials file> or         Path to file containing the credentials used to access the Rundeck REST
    --credentials=<path to credentials>      API. File is a .ini and follows the format:

                                             [credentials]
                                             apitoken=<API token string>

    -L <file path> or
    --logfilepath <file path>                Log script output to specified location.


'''

    # Attempt to use getopt for parsing
    try:
        opt_list, args = getopt.getopt(sys.argv[1:], 'hs:p:a:c:L:', ARG_VALUES.keys())
    except getopt.GetoptError:
        os.system('clear')
        print(help_string)
        sys.exit(2)

    # Assign values from options provided by user to the corresponding option
    # name in the dictionary
    for opt in opt_list:
        if opt[0] in ('-h', '--help') or len(args) > 0:
            print(help_string)
            sys.exit()
        elif opt[0] in ('-s', '--server'):
            ARG_VALUES['server='] = opt[1]
        elif opt[0] in ('-p', '--port'):
            ARG_VALUES['port='] = opt[1]
        elif opt[0] in ('-a', '--apitoken'):
            if ARG_VALUES['apitoken='] != "":
                print("ERROR: --apitoken option is not compatible with --credentials option.")
                print(help_string)
                sys.exit(1)
            ARG_VALUES['apitoken='] = opt[1]
        elif opt[0] in ('-c', '--credentials'):
            if ARG_VALUES['apitoken='] != "":
                print("ERROR: --apitoken option is not compatible with --credentials option.")
                print(help_string)
                sys.exit(1)
            # Do some error checking
            try:
                (head, tail) = os.path.split(opt[1])
                if not os.path.isdir(head):
                    print("ERROR: Invalid path (%s is not a directory) specified for --credentials option." % head)
                    sys.exit(1)
            except Exception as e:
                print(str(e))
                print("ERROR: Invalid path (%s) specified for --credentials option." % opt[1])
                sys.exit(1)
            # Parse the credentials file real quick to get the apitoken
            ARG_VALUES['credentials='] = opt[1]
            config_parser = configparser.ConfigParser()
            config_parser.read(opt[1])
            ARG_VALUES['apitoken='] = config_parser.get("credentials", "apitoken")
        elif opt[0] in ('-u', '--uuid'):
            for uuid in opt[1].split(','):
                ARG_VALUES['uuid='].append(uuid)
        elif opt[0] in ('-C', '--cmdbenvironment'):
            for cmdb_environment in opt[1].split(','):
                ARG_VALUES['cmdbenvironment='].append(cmdb_environment)
        elif opt[0] in ('-L', '--logfilepath'):
            # Do some error checking
            try:
                (head, tail) = os.path.split(opt[1])
                if not os.path.isdir(head):
                    print("ERROR: Invalid path (%s is not a directory) specified for --logfilepath option." % head)
                    sys.exit(1)
            except Exception as e:
                print(str(e))
                print("ERROR: Invalid path (%s) specified for --logfilepath option." % opt[1])
                sys.exit(1)
            ARG_VALUES['logfilepath='] = opt[1]
        elif opt[0] in ('-d', '--disableexecutions'):
            ARG_VALUES['disableexecutions'] = True
        elif opt[0] in ('-D', '--disableschedules'):
            ARG_VALUES['disableschedules'] = True

            # Make sure we have required arguments.
    if ARG_VALUES['server='] == "":
        print("ERROR: Missing value for required argument 'server=': '%s'" % ARG_VALUES['server='])
        print(help_string)
        sys.exit(1)
    elif ARG_VALUES['port='] == "":
        print("ERROR: Missing value for required argument 'port=': '%s'" % ARG_VALUES['port='])
        print(help_string)
        sys.exit(1)
    elif ARG_VALUES["apitoken="] == "":
        print("ERROR: Missing value for required argument 'apitoken=' and 'credentials=': '%s'" %
              ARG_VALUES['apitoken='])
        print(help_string)
        sys.exit(1)




#################### Main Script ##############################################
if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Process command line arguments
    process_args()

    # Setup file logging
    if not ARG_VALUES["logfilepath="] == "":
        if os.path.isfile(ARG_VALUES["logfilepath="]):
            os.remove(ARG_VALUES["logfilepath="])
        file_hdlr = logging.FileHandler(ARG_VALUES["logfilepath="])
        # add the handler to the logger
        LOGGER.addHandler(file_hdlr)

    rundeck_calendar = RundeckCalendar(ARG_VALUES['server='], ARG_VALUES['port='], ARG_VALUES['apitoken='])