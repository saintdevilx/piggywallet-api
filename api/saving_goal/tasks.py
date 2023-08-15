from django.db.models.functions import Mod, Cast, ExtractDay, Now
from django.utils import timezone

from lib.utils import logger
from mpw.celery import app
from django.db.models import functions, F, IntegerField
import json


@app.task(bind=True)
def send_saving_goal_reminder(self):
    from api.saving_goal.models import SavingGoal
    from django.db.models import ExpressionWrapper as EW, DurationField as DF
    from api.saving_goal.serializers import SavingGoalReadSerializer
    reminders = SavingGoal.get_in_progress_savings().filter(deposit_frequency__gt=0).annotate(
        time_diff=EW(Now() - F('created_at'), output_field=DF())
    ).annotate(days=Cast(ExtractDay('time_diff'), IntegerField())).annotate(
        rem=Mod('days', 'deposit_frequency')
    ).filter(rem=0)
    logger.info(('total reminders: ',reminders.count()))
    for saving in reminders:
        saving_data = SavingGoalReadSerializer(saving).data
        for device in saving.user.fcmdevice_set.filter(user=saving.user):
            device.send_message(title=saving.title, body="Today is the Saving day",
                                data={'saving': json.dumps(saving_data, default=str)})


@app.task(bind=True)
def send_saving_goal_status_change_notification(self, pk):
    """
    send notification to user about saving goal change
    from in_progress to cancel , complete , withdrawn.
    :param self:
    :param pk:
    :return:
    """
    from api.saving_goal.models import SavingGoal
    saving = SavingGoal.objects.get(pk=pk)
    from api.saving_goal.serializers import SavingGoalReadSerializer
    saving_data = json.dumps(SavingGoalReadSerializer(saving).data, default=str)
    logger.debug(('saving goal notification.....'))
    if saving.status in [SavingGoal.SAVING_GOAL_COMPLETED, SavingGoal.SAVING_GOAL_CANCELED,
                         SavingGoal.SAVING_GOAL_WITHDRAW]:
        logger.debug('sending notification....')
        for device in saving.user.fcmdevice_set.all():
            if saving.status == SavingGoal.SAVING_GOAL_COMPLETED:
                device.send_message("Congratulations", "You have achieved your goal",
                                    data={"saving":saving_data, 'reminder':False})
            else:
                device.send_message("Saving Goal Update", F"{saving.title} status changed",
                                    data={"saving":saving_data, 'reminder': False})


@app.task(bind=True)
def send_saving_goal_every_deposit_notification(self, pk):
    """

    :param self:
    :param pk:
    :return:
    """
    from api.saving_goal.models import SavingGoal
    saving = SavingGoal.objects.get(pk=pk)
    from api.saving_goal.serializers import SavingGoalReadSerializer
    saving_data = json.dumps(SavingGoalReadSerializer(saving).data, default=str)
    for device in saving.user.fcmdevice_set.all():
        device.send_message(F"{saving.title}", F"INR.{saving.deduction_amount} added to your saving goal",
                            data={"saving": saving_data, 'reminder': False, 'deposit':True})
