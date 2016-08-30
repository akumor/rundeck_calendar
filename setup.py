try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Rundeck Calendar',
    'author': 'Jan Kumor',
    'url': 'http://github.com/akumor/rundeck_calendar',
    'download_url': 'http://github.com/akumor/rundeck_calendar',
    'author_email': 'akumor@users.noreply.github.com',
    'version': '0.1',
    'install_requires': ['requests', 'ConfigParser', 'lxml'],
    'packages': ['rundeck_calendar'],
    'scripts': [],
    'name': 'rundeck_calendar'
}

setup(**config)
