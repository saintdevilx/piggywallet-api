import urllib

import requests
from django.conf import settings
from django.template.loader import render_to_string

from lib.utils import logger
from mpw.celery import app


class SmsMessage:
    """
    SMS message to be send to a number using msg91.com
        can be use to sent OTPs, Transactional message or promotional messages
    """
    message = None
    template = None
    to_number = None
    context = {}
    SMS_HOST_URL = 'http://api.msg91.com/api/sendotp.php'
    SMS_GATEWAY_URL = '{SMS_HOST_URL}?authkey={authkey}&mobile={to_number}&message={message}&sender={sender}&otp={otp}'

    def __init__(self, to_number, message=None, template=None, context={}):
        self.to_number = to_number
        self.context.update(context)
        if not message and not template:
            raise ValueError("`message` or `template` is required.")
        self.message = urllib.parse.quote(message or render_to_string(template, context=self.context))

    def send_sms(self, context={}):
        payload = {
            "SMS_HOST_URL": SmsMessage.SMS_HOST_URL,
            "authkey": settings.MSG91_AUTHKEY,
            "to_number": self.to_number,
            "message": self.message
        }
        logger.debug(context)
        if context:
            self.context.update(context)
            payload.update(self.context)
        logger.debug(payload)
        request_url = SmsMessage.SMS_GATEWAY_URL.format(**payload)
        logger.debug(F'sending otp sms ......... {request_url}')
        send_sms_async.delay(request_url)

    def send_otp_sms(self):
        self.send_sms(context={
            "sender":"MPWOTP"
        })

    def send_transaction_sms(self):
        self.send_sms(context={
            "sender":"MPW"
        })

    def send_promotional_sms(self):
        self.send_sms(context={
            "sender":"MPWP"
        })


@app.task(bind=True)
def send_sms_async(self, payload):
    """
    Send sms asynchronously (celery task) payload is the request url with parameters
    :param self:
    :param payload: encoded request url containing all the params required to send an SMS
    :return:
    """
    logger.debug(F"debug;;;.....{settings.DEBUG}")
    if settings.DEBUG:
        return
    res = requests.get(payload)
    logger.debug(F"Response: Send SMS: {res.json()}")