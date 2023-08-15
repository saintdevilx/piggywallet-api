import datetime
import urllib
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from lib.utils import logger, get_url_param
from ..models import PhoneToken
from ..utils import model_field_attr
from ...user.models import ReferredUser


class PhoneBackend(ModelBackend):
    def __init__(self, *args, **kwargs):
        self.user_model = get_user_model()

    def get_phone_number_data(self, phone_number):
        """
        Method used for filtering query.
        """
        phone_number_field = getattr(settings, 'PHONE_NUMBER_FIELD', 'phone_number')
        data = {
            phone_number_field: phone_number
        }
        return data

    def get_username(self):
        """
        Returns a UUID-based 'random' and unique username.

        This is required data for user models with a username field.
        """
        return str(uuid.uuid4())[:model_field_attr(
            self.user_model, 'username', 'max_length')]

    def create_user(self, phone_token, **extra_fields):
        """
        Create and returns the user based on the phone_token.
        """
        logger.debug(extra_fields)
        password = self.user_model.objects.make_random_password()

        username = extra_fields.get('username', self.get_username())
        password = extra_fields.get('password', password)
        logger.debug(extra_fields)
        # first_name = extra_fields.get('full_name', '').split()[:1]
        # last_name = extra_fields.get('full_name', '').split()[1:]
        kwargs = {
            'username': username,
            'password': password,
            'device_id':extra_fields.get('device_id')
            # 'first_name': first_name[0],
            # 'last_name': last_name[0] if last_name else ""
        }

        phone_number = phone_token.phone_number

        kwargs.update(self.get_phone_number_data(phone_number))
        user = self.user_model.objects.create_user(**kwargs)
        return user

    def authenticate(self, request, pk=None, otp=None, **extra_fields):
        if pk is None:
            return

        # 1. Validating the PhoneToken with PK and OTP.
        # 2. Check if phone_token and otp are same, within the given time range
        timestamp_difference = datetime.datetime.now() - datetime.timedelta(
            minutes=getattr(settings, 'PHONE_LOGIN_MINUTES', 10)
        )
        try:

            phone_token = PhoneToken.objects.get(
                pk=pk,
                otp=otp,
                used=False,
                timestamp__gte=timestamp_difference
            )
        except PhoneToken.DoesNotExist:
            phone_token = PhoneToken.objects.get(pk=pk)
            phone_token.attempts = phone_token.attempts + 1
            phone_token.save()
            raise PhoneToken.DoesNotExist

        # 3. Create new user if he doesn't exist. But, if he exists login.
        user = self.user_model.objects.filter(
            **self.get_phone_number_data(phone_token.phone_number)
        ).first()

        if not user:
            user = self.create_user(
                phone_token=phone_token,
                **extra_fields
            )
        phone_token.used = True
        phone_token.attempts += 1
        phone_token.save()
        if request.data.get('referrer') and request.data.get('device_id'):
            ref_params = request.data.get('referrer')
            ref_code = get_url_param(ref_params, 'refCode')
            logger.debug(('referrer...', ref_params, ref_code))
            ReferredUser.create(user, ref_code, request.data.get('device_id'))

        return user
