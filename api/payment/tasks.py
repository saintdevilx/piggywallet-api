from mpw.celery import app


@app.task(bind=True)
def send_new_reward_notification(reward):
    for device in reward.user.device_set.all():
        device.send_message("Congrats !!", "You got new reward ", data={"reward": True})

