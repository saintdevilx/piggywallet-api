from django.core.cache import cache
from django.utils import timezone

from emailtemplates.models import EmailTemplate
from mpw.celery import app, logger

SYNC_TIMEOUT = 60*60*12


@app.task(bind=True)
def update_user_sms_data(self, user_id, data):
    from api.user.models import  UserSMS
    key = F"{user_id}_sms"
    if cache.get(key) and (timezone.now() - cache.get(key)).seconds < SYNC_TIMEOUT:
        return
    cache.set(key, timezone.now())
    UserSMS.create(data, user_id)


@app.task(bind=True)
def update_user_contact(self, user_id, contact_list):
    from api.user.models import UserContact

    key = F"{user_id}_contact"
    if cache.get(key) and (timezone.now() - cache.get(key)).seconds < SYNC_TIMEOUT:
        logger.debug('request too earlyy............')
        return
    cache.set(key, timezone.now())
    UserContact.create(contact_list, user_id)


@app.task(bind=True)
def send_welcome_email(self):
    pass


@app.task(bind=True)
def send_verification_email(self, email, template_title, context={}):
    template = EmailTemplate.objects.get(title=template_title)
    template.send_email([email], context=context)


@app.task(bind=True)
def send_kyc_incomplete_email(self):
    pass


@app.task(bind=True)
def send_promotional_email(self):
    pass


@app.task(bind=True)
def send_monthly_saving_summary(self):
    pass