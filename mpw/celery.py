
from __future__ import absolute_import, unicode_literals

import logging
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
from mpw import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mpw.settings')
logger = logging.getLogger('celerylog')

app = Celery('mpw')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
