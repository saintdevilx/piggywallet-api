from random import randint

from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from api.reward.apps import REWARD_CASHBACK_MAX, REWARD_CASHBACK_MIN
from api.reward.tasks import send_notification_for_new_reward
from api.saving_goal.models import Transaction
from api.saving_goal.utils import current_timestamp_string
from lib.cashfree import get_cashgram_link
from lib.cashfree.webhook import PayoutWebhookEvent
from lib.core.models import BaseModel
from lib.utils import logger
from mpw.settings import AUTH_USER_MODEL
from cashfree_sdk.payouts.transfers import Transfers


class Offer(BaseModel):
    expired_on = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=100)
    short_description = models.CharField(max_length=300)
    full_description = models.TextField()
    slug = models.SlugField(blank=True)
    image = models.ImageField(null=True, blank=True)
    action_title = models.CharField(max_length=300, blank=True, null=True)
    action_url = models.CharField(max_length=500, blank=True, null=True)

    @classmethod
    def get_all_offers(cls):
        return cls.objects.all()

    def __str__(self):
        return F"{self.title}"

    class Meta:
        ordering = ['-created_at']


class Reward(BaseModel):
    REWARD_TYPE_CASH_BACK = 0
    REWARD_TYPE_COUPON = 1
    REWARD_TYPE_CHOICES = (
        (REWARD_TYPE_CASH_BACK, 'CASHBACK'),
        (REWARD_TYPE_COUPON, 'COUPON')
    )

    REWARD_STATUS_PENDING = 0
    REWARD_STATUS_SUCCESS = 1
    REWARD_STATUS_FAILED = 2
    REWARD_STATUS_UNOPENED = 3
    REWARD_STATUS_OPENED = 4
    REWARD_STATUS_CHOICES = (
        (REWARD_STATUS_PENDING, "PENDING"),
        (REWARD_STATUS_SUCCESS, "SUCCESS"),
        (REWARD_STATUS_FAILED, "FAILED"),
        (REWARD_STATUS_UNOPENED, "UNOPENED"),
        (REWARD_STATUS_OPENED, "OPENED")
    )
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE)
    reward_id = models.CharField(max_length=20,  null=True, unique=True, default=current_timestamp_string)
    type = models.SmallIntegerField(choices=REWARD_TYPE_CHOICES)
    amount = models.DecimalField(decimal_places=2, default=0, max_digits=5)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, null=True, blank=True)
    earned_for = models.TextField()
    status = models.SmallIntegerField(choices=REWARD_STATUS_CHOICES, default=REWARD_STATUS_UNOPENED)
    expire_on = models.DateTimeField(null=True, blank=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    cashgram_url = models.CharField(max_length=500, null=True, blank=True)
    bank_account = models.ForeignKey('user.UserBankAccount', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)

    @property
    def title(self):
        return F"{self.get_status_display()} {self.amount}"

    def __str__(self):
        return F"{self.get_type_display()}-{self.amount}"

    @classmethod
    def add_reward(cls, user, earned_for=None, offer=None, transaction=None, type=None, status=None):
        status = status or cls.REWARD_STATUS_PENDING
        amount = randint(int(REWARD_CASHBACK_MIN), int(REWARD_CASHBACK_MAX))
        return cls.objects.create(user=user, earned_for=earned_for, offer=offer, transaction=transaction, type=type,
                                  status=status, amount=amount)

    @classmethod
    def get_reward_for_user(cls, user):
        return cls.objects.filter(user=user)

    @classmethod
    def process_reward(cls, payout_webhook_response):
        data = payout_webhook_response
        transfer_id = data.transfer_id.replace('reward_','')
        with transaction.atomic():
            reward = cls.objects.select_for_update().get(reward_id=transfer_id)
            if reward.status in (reward.REWARD_STATUS_PENDING, reward.REWARD_STATUS_OPENED):
                if payout_webhook_response.event == PayoutWebhookEvent.TRANSFER_SUCCESS:
                    reward.status = cls.REWARD_STATUS_SUCCESS
                elif payout_webhook_response.event == PayoutWebhookEvent.TRANSFER_FAILED:
                    reward.status = cls.REWARD_STATUS_FAILED
                else:
                    reward.status = cls.REWARD_STATUS_FAILED
                reward.save()

    def generate_cashgram_url(self):
        data = get_cashgram_link(self)
        self.reference_id = data.get('referenceId')
        self.cashgram_url = data.get('cashgramLink')
        self.expire_on = timezone.localdate() + timezone.timedelta(days=6)

    def set_opened(self):
        self.status = self.REWARD_STATUS_OPENED
        # if not self.cashgram_url:
        #     self.generate_cashgram_url()
        self.save()

    def redeem_reward(self, bank_account, comment="", data={}, extra_data={}):
        if self.REWARD_STATUS_UNOPENED or self.REWARD_STATUS_OPENED:
            _type = Transaction.TRANSACTION_TYPE_DEBIT
            status = Transaction.TRANSACTION_STATUS_PENDING
            self.status = self.REWARD_STATUS_PENDING
            self.bank_account = bank_account
            self.save()
            logger.debug(("transferring rewardd...", self.amount, self.amount))
            tnx_req = Transfers.request_transfer(beneId=str(self.bank_account_id).replace('-',''),
                                                 amount=F"{self.amount}",
                                                 transferId=F"reward_{self.reward_id}",
                                                 transferMode="upi" if self.bank_account.upi_vpa else "banktransfer",
                                                 remarks="MPW Saving goal withdraw ")
            logger.debug(("transfer id", self.pk, tnx_req.json()))
            return tnx_req


@receiver(post_save,sender=Reward)
def post_new_reward_added(sender, instance, **kwargs):
    if kwargs.get('created'):
        send_notification_for_new_reward.delay(instance.user_id)
    instance.user.sync_reward_count()