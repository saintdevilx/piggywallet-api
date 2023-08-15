import dj_database_url
from django.core.exceptions import ImproperlyConfigured

DATABASES = {}
DATABASES['default'] = dj_database_url.config(env='DATABASE_URL', conn_max_age=600)


def get_from_environment(var_name, fail_silently=False):
    try:
        var = os.environ[var_name]
        return var
    except KeyError:
        if fail_silently:
            return ''
        raise ImproperlyConfigured(var_name + " variable not found in the environment.")

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static asset configuration
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

CELERY_BROKER_URL = os.environ.get('CLOUDAMQP_URL', 'amqp://guest@localhost:5672/')
BROKER_URL = CELERY_BROKER_URL
# CELERY_ALWAYS_EAGER = False
# CELERY_TASK_ALWAYS_EAGER = False

# CORS_ORIGIN_WHITELIST = [ 'http://dev.mypiggywallet.com' ]
CORS_ORIGIN_ALLOW_ALL = True if get_from_environment('CORS_ORIGIN_ALLOW_ALL') else False
