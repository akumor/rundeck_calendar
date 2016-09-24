#!/usr/bin/env python
"""

"""
# TODO add Google Calendar output https://github.com/fabriceb/gcalcron
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
import requests
import lxml.etree as etree


class RundeckCalendar:
    """
    Class used to produce different representations of Rundeck job schedule data.
    """

    class RundeckJobSchedule:
        """
        Class used to store data about Rundeck jobs related to their schedule.
        """

        def __init__(self, uuid, name, project, group=None, cron_schedule=None, second=None, minute=None, hour=None,
                     day_of_month=None, month=None, day_of_week=None, year=None):
            """
            :param uuid: UUID of the Rundeck job
            :param name: Name of the Rundeck job
            :param project: Project that the Rundeck job belongs to
            :param group: Group the Rundeck job belongs to
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
            self.group = group
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
                self.logger.debug(self.project + ':' + self.name + ': ' + cron_schedule)
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
        self.rundeck_job_schedules = self._get_rundeck_job_schedules()

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
            self.logger.debug('Get project name response:\n%s' % resp.text)
            doc = etree.fromstring(resp.text)
            project_names = []
            for projects in doc:
                for name in projects.findall('project'):
                    self.logger.debug('name.find("name").text:\n%s' % name.find('name').text)
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
                        try:
                            rundeck_job_schedule = self.RundeckJobSchedule(job.find('id').text,
                                                                           job.find('name').text,
                                                                           project_name,
                                                                           group=job.find('group').text)
                        except AttributeError:
                            rundeck_job_schedule = self.RundeckJobSchedule(job.find('id').text,
                                                                           job.find('name').text,
                                                                           project_name)
                        try:
                            rundeck_job_schedule.cron_schedule = sched.attrib['crontab']
                        except (AttributeError, KeyError) as e:
                            try:
                                rundeck_job_schedule.second = sched.find('time').attrib['seconds']
                            except (AttributeError, KeyError) as e:
                                pass
                            try:
                                rundeck_job_schedule.minute = sched.find('time').attrib['minute']
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
                            try:
                                rundeck_job_schedule.day_of_month = sched.find('month').attrib['day']
                            except (AttributeError, KeyError):
                                pass

                        rundeck_job_schedules.append(rundeck_job_schedule)
        return rundeck_job_schedules

    def get_schedule_summary(self):
        """
        Returns a string containing the Rundeck cron schedules of all the jobs in this "Calendar".
        :return: string
        """
        summary = "project:job: second minute hour day_of_month month day_of_week year\n"
        for run_sched in self.rundeck_job_schedules:
            summary += run_sched.project + ':'
            if run_sched.group is not None:
                summary += run_sched.group + '/'
            summary += run_sched.name + ': '
            summary += run_sched.second + ' '
            summary += run_sched.minute + ' '
            summary += run_sched.hour + ' '
            summary += run_sched.day_of_month + ' '
            summary += run_sched.month + ' '
            summary += run_sched.day_of_week + ' '
            summary += run_sched.year + '\n'
        return summary
