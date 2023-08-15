from cashfree_sdk.payouts.transfers import Transfers
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from api.payment.exceptions import InvalidSubscriptionDetails
from api.saving_goal.models import SavingGoal, User, Transaction
from api.saving_goal.utils import current_timestamp_string
from api.user.models import UserBankAccount
from lib.cashfree.subscription import CashFreeSubscription
from lib.cashfree.webhook import PayoutWebhookEvent
from lib.core.models import BaseModel
from lib.utils import logger


class UserWithdrawRequest(BaseModel):
    """
    to store user withdraw request that will be fullfilled via NEFT
    """
    WITHDRAW_PENDING = 0
    WITHDRAW_SUCCESS = 1
    WITHDRAW_FAILED = 2
    WITHDRAW_CANCELLED = 3
    WITHDRAW_STATUS_CHOICES = (
        (WITHDRAW_PENDING, 'PENDING'), (WITHDRAW_SUCCESS, "SUCCESS"), (WITHDRAW_FAILED, 'FAILED'),
        (WITHDRAW_CANCELLED, 'CANCELLED')
    )
    saving_goal = models.ForeignKey(SavingGoal, on_delete=models.CASCADE)
    withdraw_amount = models.DecimalField(max_digits=10, decimal_places=2)
    user_bank_account = models.ForeignKey(UserBankAccount, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.SmallIntegerField(choices=WITHDRAW_STATUS_CHOICES, default=WITHDRAW_PENDING)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, default=None, null=True)
    reference_id = models.CharField(max_length=100, null=True)
    utr = models.CharField(max_length=100, null=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return F"{self.withdraw_amount} {self.get_status_display()}"

    @staticmethod
    def process_withdraw_request(payout_webhook_response):
        data = payout_webhook_response
        with transaction.atomic():
            withdraw_request = UserWithdrawRequest.objects.select_for_update().get(pk=data.transfer_id)
            if payout_webhook_response.event == PayoutWebhookEvent.TRANSFER_SUCCESS:
                assert withdraw_request.saving_goal.current_amount >= withdraw_request.withdraw_amount
                withdraw_request.transaction.status = Transaction.TRANSACTION_STATUS_SUCCESS
                withdraw_request.transaction.amount_before = withdraw_request.saving_goal.current_amount
                withdraw_request.transaction.amount_after = withdraw_request.saving_goal.current_amount - withdraw_request.withdraw_amount
                withdraw_request.transaction.save()

                SavingGoal.withdraw(withdraw_request.saving_goal_id, withdraw_request.withdraw_amount, withdraw_request.user)
                withdraw_request.status = withdraw_request.WITHDRAW_SUCCESS
                withdraw_request.save()
            elif payout_webhook_response.event == PayoutWebhookEvent.TRANSFER_FAILED:
                withdraw_request.transaction.status = Transaction.TRANSACTION_STATUS_FAILED
                withdraw_request.transaction.save()
                withdraw_request.status = withdraw_request.WITHDRAW_FAILED
                withdraw_request.save()

        # TODO: complete the withdraw flow

    @classmethod
    def get_withdraw_request(cls, filter_by=None, order_by=None, search_by=None, status=None):
        qry = cls.objects.all().prefetch_related('user').prefetch_related('user_bank_account')
        if filter_by:
            qry = qry.filter(**filter_by)
        if status:
            qry = qry.filter(status=status)
        if order_by:
            qry = qry.order_by(F"{order_by}")
        elif search_by:
            qry = qry.filter(Q(saving_goal_pk=search_by)|Q(user__first_name=search_by)|Q(user__last_name=search_by))
        return qry

    def cancel_withdraw_request(self):
        self.status = self.WITHDRAW_CANCELLED
        self.save()
        if self.transaction:
            self.transaction.cancel_transaction()

    def initiate_withdraw(self):
        if self.status == self.WITHDRAW_PENDING:
            tnx_req = Transfers.request_transfer(beneId=str(self.user_bank_account_id).replace('-',''),
                                                 amount=F"{self.withdraw_amount}",
                                                 transferId=str(self.pk).replace('-',''),
                                                 transferMode="upi" if self.user_bank_account.upi_vpa else "banktransfer",
                                                 remarks="MPW Saving goal withdraw ")
            return tnx_req
        return False


class PaymentSubscription(BaseModel):
    """

    """
    SUBSCRIPTION_ACTIVE = 1
    SUBSCRIPTION_PENDING = 0
    SUBSCRIPTION_CANCELLED = 2
    SUBSCRIPTION_STATUS_CHOICES = (
        (SUBSCRIPTION_ACTIVE, 'ACTIVE'), (SUBSCRIPTION_PENDING, 'PENDING'), (SUBSCRIPTION_CANCELLED, 'CANCELLED')
    )
    saving_goal = models.ForeignKey(SavingGoal, on_delete=models.CASCADE)
    subscription_id = models.CharField(max_length=100)
    reference_id = models.CharField(max_length=100)
    auth_link = models.TextField(max_length=500)
    status = models.SmallIntegerField(default=0, choices=SUBSCRIPTION_STATUS_CHOICES)
    extra_data = models.TextField()

    def __str__(self):
        return F"{self.subscription_id} {self.reference_id}"

    @staticmethod
    def create_subscription(saving, user):
        """
        create subscription and generating payment authorisation link
        """
        subscription = CashFreeSubscription()
        timestamp = str(timezone.now().timestamp()).replace('.','')
        plan_id = F"saving{timestamp}"
        sub_id = F"sub{timestamp}"

        response = subscription.create(plan_id=plan_id, plan_name=saving.title, amount=float(saving.deduction_amount),
                                       interval_type=saving.deposit_frequency)
        if response.ok:
            response = subscription.subscribe(plan_id=plan_id, subscription_id=sub_id,
                                              customer_name=user.get_full_name(), customer_email=user.get_email(),
                                              customer_phone=user.get_phone_number(),
                                              expires_on=saving.target_date.strftime('%Y-%m-%d %H:%M:%S'))
            if response:
                return PaymentSubscription.objects.create(
                    saving_goal=saving, subscription_id=sub_id, reference_id=response.get('subReferenceId'),
                    auth_link=response.get('authLink'), extra_data=response
                )
            else:
                logger.debug(response.json())
                raise InvalidSubscriptionDetails(response.json())
        else:
            logger.debug(response.json())
            raise InvalidSubscriptionDetails(response.json())

    def get_subscription_details(self, reference_id):
        return CashFreeSubscription().get_subscription_details(reference_id)

    def synchronise_subscription_status(self, reference_id):
        data = PaymentSubscription.get_subscription_details(reference_id)
        if data:
            self.status = self.SUBSCRIPTION_ACTIVE if data['status'] == 'ACTIVATED' else self.SUBSCRIPTION_PENDING
            self.save()
        return data

    def update_status(self, response_data):
        logger.debug(F"RESPONSE- STATUS:{response_data['cf_status'] == 'ACTIVE'}")
        self.status = self.SUBSCRIPTION_ACTIVE if response_data['cf_status'] == 'ACTIVE' else self.SUBSCRIPTION_PENDING
        self.save()
        if self.status == self.SUBSCRIPTION_ACTIVE:
            self.saving_goal.set_payment_subscription(True)

    @classmethod
    def get_user_subscriptions(cls, user):
        return cls.objects.prefetch_related('saving_goal').filter(saving_goal__user=user)

    def cancel_subscription(self, user):
        if self.saving_goal.user_id == user.pk:
            response = CashFreeSubscription().unsubscribe(self.reference_id)
            if response and response['status'] == 'OK':
                self.status = self.SUBSCRIPTION_CANCELLED
                self.save()
                self.saving_goal.set_payment_subscription(False)
                return response
