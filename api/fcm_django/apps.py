from django.apps import AppConfig
from .settings import FCM_DJANGO_SETTINGS as SETTINGS


class FcmDjangoConfig(AppConfig):
    name = 'fcm_django'
    verbose_name = SETTINGS["APP_VERBOSE_NAME"]
