from api.fcm_django.models import FCMDevice
from mpw.celery import app


@app.task(bind=True)
def send_notification_for_new_reward(self, user_pk):
    for device in FCMDevice.objects.filter(user=user_pk):
        device.send_message(title="Congratulations !!", body="You won a reward.",
                            data={'reward': True})