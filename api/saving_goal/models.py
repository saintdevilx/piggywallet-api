import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.utils import timezone

from api.saving_goal.exceptions import InsufficientBalance, NotAuthorisedUser, NegativeAmount, InvalidModelObject
from api.saving_goal.tasks import send_saving_goal_every_deposit_notification, \
    send_saving_goal_status_change_notification
from api.saving_goal.utils import current_timestamp_string
from lib.cashfree.payment_gateway import UPIGateway, UPIOrderStatus
from lib.cashfree.webhook import AutoCollectWebhookEvent
from lib.core.models import BaseModel
import tagulous.models

from lib.paytm.models import PaymentStatus, PaymentStatusExtended
from lib.paytm.paytm_utils import get_payment_status
from lib.utils import logger
from mpw import settings

User = get_user_model()


class SavingGoal(BaseModel):
    """
    Saving goal Plan to save money
    """
    SAVING_GOAL_IN_PROGRESS = 0
    SAVING_GOAL_COMPLETED = 1
    SAVING_GOAL_CANCELED = 2
    SAVING_GOAL_WITHDRAW = 3

    SAVING_GOAL_STATUS_CHOICES = (
        (SAVING_GOAL_IN_PROGRESS, "In Progress"), (SAVING_GOAL_COMPLETED, "Completed"),
        (SAVING_GOAL_CANCELED, "Canceled"), (SAVING_GOAL_WITHDRAW, "Withdraw")
    )
    DEPOSIT_MANUAL = 0
    DEPOSIT_DAILY = 1
    DEPOSIT_WEEKLY = 7
    DEPOSIT_MONTHLY = 30
    DEPOSIT_FREQUENCY_CHOICES = (
        (DEPOSIT_DAILY, 'daily'), (DEPOSIT_WEEKLY, 'weekly'), (DEPOSIT_MONTHLY, 'monthly')
    )

    MANUAL_DEBIT = 0
    AUTO_DEBIT = 1
    DEDUCTION_MODE_CHOICES = (
        (AUTO_DEBIT, 'AUTO DEBIT'), (MANUAL_DEBIT, 'MANUAL DEBIT')
    )

    title = models.CharField(max_length=100, help_text="Money saving for")
    user = models.ForeignKey(User, related_name='created_by', on_delete=models.CASCADE)
    target_amount = models.DecimalField(max_digits=8, decimal_places=2, help_text="Amount to be save")
    current_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    target_date = models.DateTimeField(default=None, null=True)
    contributors = models.ManyToManyField(User, null=True, through='SavingGoalContributor')
    status = models.SmallIntegerField(choices=SAVING_GOAL_STATUS_CHOICES, default=SAVING_GOAL_IN_PROGRESS)
    deposit_frequency = models.SmallIntegerField(choices=DEPOSIT_FREQUENCY_CHOICES, default=DEPOSIT_MANUAL)
    deduction_mode = models.SmallIntegerField(choices=DEDUCTION_MODE_CHOICES, default=AUTO_DEBIT)
    deduction_amount = models.DecimalField(max_digits=8, decimal_places=2, help_text="", default=0)
    last_deposited = models.DateTimeField(null=True)
    payment_subscription = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return F"{self.title} {self.get_status_display()}"

    def set_payment_subscription(self, status):
        self.payment_subscription = status
        self.save()

    def get_deduction_amount(self, target_date, amount, frequency):
        try:
            total_days = (target_date - timezone.now()).days
            if frequency in [self.DEPOSIT_DAILY, self.DEPOSIT_WEEKLY, self.DEPOSIT_MONTHLY ]:
                return round(amount / (total_days // frequency), 2)
        except Exception as ex:
            logger.exception('get deduction amount error')
        return 0

    @staticmethod
    def get_saving_goals(user, status=None):
        qs = SavingGoal.objects.filter(user=user)
        if status is not None:
            qs = qs.filter(status=status)
        return qs

    def get_current_amount(self):
        return self.current_amount

    # def send_reminder(self):
    #     send_reminder_notification.delay(self.pk)

    #@classmethod
    def deposit(self, amount):
        """
        deposit money to saving goal
        :param user:
        :param pk:
        :param amount: amount to be deposit
        :return:
        """
        with transaction.atomic():
            update_fields = ['current_amount']
            account = self
            account.current_amount += amount
            if abs(account.current_amount) >= abs(account.target_amount):
                account.status = account.SAVING_GOAL_COMPLETED
                update_fields.append('status')

            account.last_deposited = timezone.now()
            account.save(update_fields=update_fields)
            self.user.set_current_amount(self.user.current_deposit + amount)
            logger.debug('Updated.....')
            # send notification about new deposit
            send_saving_goal_every_deposit_notification.delay(self.pk)

    def sync_goal_status_count(self):
        goals = dict(map(lambda x: (x['status'], x['count']), SavingGoal.objects.filter(user=self.user).
                         values('status').annotate(count=Count('status')).order_by()))
        logger.debug(goals)
        self.user.in_progress_goal = goals.get(self.SAVING_GOAL_IN_PROGRESS, 0)
        self.user.achieved_goal = goals.get(self.SAVING_GOAL_COMPLETED, 0)
        self.user.save()

    @classmethod
    def withdraw(cls, pk, amount, user):
        """
        withdraw money from saving goal
        :param pk:
        :param user: user making withdraw request
        :param amount: amount to be withdraw
        :return:
        """

        with transaction.atomic():
            account = get_object_or_404(cls.objects.select_for_update(), pk=pk, user=user)
            logger.debug(account.current_amount)
            logger.debug(amount)
            if float(account.current_amount) < float(amount):
                raise InsufficientBalance("Insufficient balance to withdraw")
            elif account.user.pk != user.pk:
                raise NotAuthorisedUser("Not authorised user to withdraw from this saving account")
            account.current_amount -= amount
            account.save()
            user.set_current_amount(user.current_deposit- amount)

    @classmethod
    def get_transactions(cls, obj):
        return Transaction.objects.exclude(status=Transaction.TRANSACTION_STATUS_INITIATED).\
            filter(associated_pk=obj.pk,content_type=ContentType.objects.get_for_model(obj)).order_by('-created_at')

    def close_saving(self):
        with transaction.atomic():
            self.status = self.SAVING_GOAL_CANCELED
            self.save(update_fields=['status'])

    @staticmethod
    def get_in_progress_savings():
        return SavingGoal.objects.filter(status=SavingGoal.SAVING_GOAL_IN_PROGRESS)


class SavingGoalContributor(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    saving_goal = models.ForeignKey(SavingGoal, on_delete=models.CASCADE)


class Transaction(BaseModel):
    """
    Transaction history for all the transaction made across th platform
    """
    TRANSACTION_TYPE_DEBIT = 0
    TRANSACTION_TYPE_CREDIT = 1

    TRANSACTION_TYPE_CHOICES = (
        (TRANSACTION_TYPE_DEBIT, "DEBIT"), (TRANSACTION_TYPE_CREDIT, "CREDIT"),
    )

    TRANSACTION_STATUS_INITIATED = 0
    TRANSACTION_STATUS_PENDING = 4
    TRANSACTION_STATUS_SUCCESS = 1
    TRANSACTION_STATUS_FAILED = 2
    TRANSACTION_STATUS_CANCELLED = 3
    TRANSACTION_STATUS_CHOICES = (
        (TRANSACTION_STATUS_PENDING, 'PENDING'), (TRANSACTION_STATUS_SUCCESS, 'SUCCESS'),
        (TRANSACTION_STATUS_FAILED, 'FAILED'), (TRANSACTION_STATUS_CANCELLED, 'CANCELLED'),
        (TRANSACTION_STATUS_INITIATED, 'INITIATED')
    )
    order_id = models.CharField(max_length=20, default=current_timestamp_string, null=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_before = models.DecimalField(max_digits=10, decimal_places=2)
    amount_after = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.SmallIntegerField(choices=TRANSACTION_TYPE_CHOICES)
    status = models.SmallIntegerField(choices=TRANSACTION_STATUS_CHOICES, default=TRANSACTION_STATUS_INITIATED)
    data = models.TextField()
    extra_data = models.TextField()
    comment = models.TextField()

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    associated_pk = models.CharField(max_length=300)
    associated_object = GenericForeignKey('content_type', 'associated_pk')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return F"{self.amount} {self.get_type_display()} {self.get_status_display()}"

    @classmethod
    def create(cls, user, model_object, _type, amount, status=None, comment="", data={}, extra_data={}):
        """

        :param user:
        :param model_object:
        :param _type:
        :param amount:
        :param status:
        :param comment:
        :param data:
        :param extra_data:
        :return:
        """

        # if depositing amount to saving goal check if user has VPA if not create one
        if cls.TRANSACTION_TYPE_CREDIT and (settings.VIRTUAL_ACCOUNT_ENABLED and not user.get_virtual_account()):
            user.create_virtual_account()

        if amount < 0:
            raise NegativeAmount("Amount can't be negative")

        if not hasattr(model_object, 'get_current_amount'):
            raise InvalidModelObject(F"Invalid model object {type(model_object)} does not have "
                                     F"`get_current_amount` method")

        current_amount = model_object.get_current_amount()
        if float(current_amount) < float(amount) and _type == cls.TRANSACTION_TYPE_DEBIT:
            raise InsufficientBalance("Insufficient balance")
        amount_before = current_amount
        amount_after = amount_before - (amount if _type == cls.TRANSACTION_TYPE_DEBIT else - amount)
        return cls.objects.create(
            user=user, amount=amount, amount_before=amount_before,
            amount_after=amount_after, status=status,
            comment=comment, data=data, extra_data=extra_data,
            associated_object=model_object, type=_type
        )

    @classmethod
    def update_status(cls, order_id, status, amount=None, data={}):
        with transaction.atomic():
            transaction_row = cls.objects.select_for_update().get(order_id=order_id,
                                                                  status__in=[cls.TRANSACTION_STATUS_PENDING,
                                                                              cls.TRANSACTION_STATUS_INITIATED])
            if status.upper() == 'SUCCESS':
                _status = cls.TRANSACTION_STATUS_SUCCESS
            elif status.upper() == 'FAILED':
                _status = cls.TRANSACTION_STATUS_FAILED
            elif status.upper() == 'PENDING':
                _status = cls.TRANSACTION_STATUS_PENDING
            logger.debug(status)
            transaction_row.status = _status
            if amount:
                transaction_row.amount = Decimal(amount)
            transaction_row.save()
            if status.upper() == 'SUCCESS':
                transaction_row.associated_object.deposit(transaction_row.amount)
            return transaction_row

    @classmethod
    def autocollect_update_event(cls, event_data):
        status = "SUCCESS" if event_data.event == AutoCollectWebhookEvent.AMOUNT_COLLECTED else "FAILURE"
        order_id = event_data.reference_id
        try:
            cls.update_status(order_id, status, amount=event_data.amount)
        except:
            pass

    @classmethod
    def get_all_transaction(cls, user, order_by=None, type=None, timeline=None):
        transactions = cls.objects.filter(user=user).exclude(status=cls.TRANSACTION_STATUS_INITIATED)
        if order_by:
            transactions = transactions.order_by('-created_at' if order_by == 'latest' else 'created_at')
        if type:
            transactions = transactions.filter(type=cls.TRANSACTION_TYPE_CREDIT if type.upper() == 'CREDIT'
            else cls.TRANSACTION_TYPE_DEBIT)
        if timeline:
            timeline = timezone.now() - timedelta(days=int(timeline))
            transactions = transactions.filter(created_at__gte=timeline)
        # logger.debug(transactions.query.__str__())
        return transactions

    def get_status(self):
        return self.status

    def cancel_transaction(self):
        assert self.status == self.TRANSACTION_STATUS_PENDING or self.status == self.TRANSACTION_STATUS_INITIATED
        self.status = self.TRANSACTION_STATUS_CANCELLED
        self.save()

    def get_or_set_status(self, order_id):
        """
        method will return the transaction and payment status received from payment gateway
        :param pk:
        :param order_id:
        :return:
        """
        try:

            payment_status_res = dict(UPIGateway().get_order_status(order_id).get_data())
            status = payment_status_res['orderStatus']
            _status = "SUCCESS" if status == UPIOrderStatus.PAID else "PENDING" \
                if status == UPIOrderStatus.ACTIVE else "FAILURE"
            if self.status in [self.TRANSACTION_STATUS_INITIATED, self.TRANSACTION_STATUS_PENDING] and _status == "SUCCESS":
                return Transaction.update_status(self.order_id, _status),None
            return self, None
        except:
            logger.exception("error while fetchign status")
            return (None, None)


    def get_data_json(self):
        try:
            return PaymentStatus(json.loads(self.data))
        except:
            return {}

    @classmethod
    def has_active_withdraw_request_for_user(cls, user):
        """
        return whether a withdraw request for provide user object exists or not
        :param user:
        :return: boolean
        """
        return cls.objects.filter(user=user, type=Transaction.TRANSACTION_TYPE_DEBIT,
                                  status__in=[Transaction.TRANSACTION_STATUS_INITIATED,
                                              Transaction.TRANSACTION_STATUS_PENDING]).exists()


@receiver(post_save, sender=SavingGoal)
def post_save_saving_goal(sender, instance, **kwargs):
    if kwargs.get('update_fields') and 'status' in kwargs.get('update_fields'):
        logger.info(F"{instance.title} : status changed from {instance.get_status_display()} ")
        send_saving_goal_status_change_notification.delay(instance.pk)
    instance.sync_goal_status_count()