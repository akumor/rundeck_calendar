#!/usr/bin/env python
import signal
import os
import logging
import sys
import getopt
import configparser
from rundeck_calendar import RundeckCalendar

# Setup logging
LOGGER_NAME = __name__
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
              "logfilepath=": "",
              "summary": False
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

    -S or --summary                          Prints a summary of the job schedules to the console in Rundeck cron
                                             format.

    -L <file path> or
    --logfilepath <file path>                Log script output to specified location.


'''

    # Attempt to use getopt for parsing
    try:
        opt_list, args = getopt.getopt(sys.argv[1:], 'hs:p:a:c:SL:', ARG_VALUES.keys())
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
        elif opt[0] in ('-S', '--summary'):
            ARG_VALUES['summary'] = True
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

if ARG_VALUES['summary']:
    LOGGER.info('Rundeck Schedule Summary:\n' + rundeck_calendar.get_schedule_summary())

LOGGER.info("Script Completed.")
sys.exit(0)
