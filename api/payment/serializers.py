from urllib.parse import urlparse

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from api.payment.models import UserWithdrawRequest, PaymentSubscription
from api.saving_goal.exceptions import ActiveWithdrawRequest, InsufficientBalance
from api.saving_goal.models import Transaction
from api.saving_goal.serializers import SavingGoalWriteSerializer, SavingGoalReadSerializer
from lib.cashfree import CFResponse
from lib.utils import logger
from mpw import settings


class UserWithdrawRequestWriteSerializer(ModelSerializer):
    """
    UserWithdrawRequest serializer for taking request data and writing to database
    """
    class Meta:
        model = UserWithdrawRequest
        fields = ['pk', 'user_bank_account', 'withdraw_amount', 'saving_goal']

    def create_withdraw_request(self, user):
        """
        create a withdraw request that will be periodically processed after verifying
        :param saving_goal:
        :param user:
        :return:
        """
        logger.debug(self.validated_data['saving_goal'])
        if Transaction.has_active_withdraw_request_for_user(user):
            raise ActiveWithdrawRequest("Only one withdraw request can exist at a time")
        # If amount debited from the wallet
        elif self.validated_data['saving_goal'].current_amount < self.validated_data['withdraw_amount']:
            raise InsufficientBalance("Insufficient balance to withdraw")
        logger.debug(self.validated_data)
        self.validated_data['user'] = user
        self.save()
        transaction = Transaction.create(user, self.validated_data['saving_goal'], Transaction.TRANSACTION_TYPE_DEBIT,
                                         self.instance.withdraw_amount, status=Transaction.TRANSACTION_STATUS_PENDING)
        self.instance.transaction = transaction
        self.instance.save()
        try:
            response = self.instance.initiate_withdraw()
            res = CFResponse().set_response(response)
            if res.status == "SUCCESS":
                data = response.json()
                UserWithdrawRequest.process_withdraw_request()
            logger.debug(('withdraw request response:', response, response.json()))
        except:
            logger.exception("withdraw initiate...")


class PaymentSubscriptionSerializer(ModelSerializer):
    auth_link = serializers.SerializerMethodField()

    class Meta:
        model = PaymentSubscription
        fields = ('auth_link', 'reference_id', 'status', 'subscription_id', 'saving_goal')

    def get_auth_link(self, obj):
        if not settings.DEBUG:
            parsed_url = urlparse(obj.auth_link)
            if parsed_url.scheme == 'http':
                return parsed_url.geturl().replace('http','https')
        return obj.auth_link


class PaymentSubscriptionListSerializer(ModelSerializer):
    saving_goal = SavingGoalReadSerializer()
    status = serializers.SerializerMethodField()
    class Meta:
        model = PaymentSubscription
        fields = ('pk', 'reference_id', 'status', 'subscription_id', 'saving_goal')

    def get_status(self, obj):
        return obj.get_status_display()