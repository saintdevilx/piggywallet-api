from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers

from api.saving_goal.exceptions import InsufficientBalance, NotAuthorisedUser, VirtualAccountCreationFailed, \
    ActiveWithdrawRequest
from api.saving_goal.models import SavingGoal, Transaction
from api.user.models import VirtualAccount
from lib.utils import logger


class SavingGoalWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingGoal
        UPDATABLE_FIELDS = ['title', 'target_amount', 'target_date', 'deposit_frequency']
        fields = UPDATABLE_FIELDS + ['user']

    def set_date(self):
        self.target_date = parse_date(self.target_date)

    def create_update_saving_goal(self, instance=None):
        logger.debug(self.validated_data)
        [self.validated_data.pop(k) for k, v in self.validated_data.items() if k not in self.Meta.fields]
        self.validated_data['deduction_amount'] = self.get_deduction_amount(self.validated_data['target_date'],
                                                          float(self.validated_data['target_amount']) - (float(instance.current_amount) if instance else 0),
                                                          int(self.validated_data['deposit_frequency']))
        logger.debug(self.validated_data['deduction_amount'])
        if instance:
            return self.update(instance, self.validated_data)
        return self.save()

    def get_deduction_amount(self, target_date, amount, frequency):
        try:
            total_days = (target_date - timezone.now()).days
            if frequency in [self.Meta.model.DEPOSIT_DAILY, self.Meta.model.DEPOSIT_WEEKLY,
                             self.Meta.model.DEPOSIT_MONTHLY]:
                return round(amount / (total_days // frequency), 2)
        except Exception as ex:
            pass
        return 0

    def get_updatable_data(self):
        return {k:v for k,v in self.validated_data.items() if k in self.Meta.UPDATABLE_FIELDS}


class SavingGoalReadSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    time_left = serializers.SerializerMethodField()
    target_date = serializers.SerializerMethodField()

    class Meta:
        model = SavingGoal
        fields = ['pk', 'title', 'target_amount', 'status', 'current_amount', 'created_at', 'target_date', 'user',
                  'deposit_frequency', 'deduction_mode', 'deduction_amount', 'last_deposited', 'time_left',
                  'payment_subscription']

    def get_target_date(self, obj):
        if not obj.target_date:
            return
        #logger.debug(obj.target_date)
        return obj.target_date.date()

    def get_status(self, obj):
        return obj.get_status_display()

    def get_deposit_frequency(self, obj):
        return obj.get_deposit_frequency_display()

    def get_deduction_mode(self, obj):
        return obj.get_deduction_mode_display()

    def get_deduction_mode(self, obj):
        return obj.get_deduction_mode_display()

    def get_deposit_frequency(self, obj):
        return obj.get_deposit_frequency_display()

    def get_time_left(self, obj):
        if not obj.target_date:
            return
        return (obj.target_date - timezone.now()).days


class SavingGoalTransactionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['pk', 'amount', 'type', 'user', 'status', 'order_id']

    def get_status(self):
        return self.get_status_display()

    def get_type(self):
        return self.get_type_display()


class SavingGoalTransactionSerializer(serializers.Serializer):
    TRANSACTION_TYPE_CHOICES = [
        ('DEBIT', Transaction.TRANSACTION_TYPE_DEBIT),
        ('CREDIT', Transaction.TRANSACTION_TYPE_CREDIT),
    ]
    saving_goal_pk = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    type = serializers.CharField(max_length=100)

    class Meta:
        fields = ['saving_goal_pk', 'amount', 'type']

    def create_transaction(self, user):
        """

        :param user:
        :return:
        """
        try:
            validated_data = self.validated_data
            saving_goal_object = get_object_or_404(SavingGoal, pk=validated_data['saving_goal_pk'])
            amount = saving_goal_object.deduction_amount

            # If amount debited from the wallet
            if validated_data['type'] == str(Transaction.TRANSACTION_TYPE_DEBIT) \
                    and saving_goal_object.current_amount < amount:
                raise InsufficientBalance("Insufficient balance to withdraw")
            elif saving_goal_object.user.pk != user.pk:
                raise NotAuthorisedUser("Not authorised user to withdraw from this saving account")

            instance = Transaction.create(
                model_object=saving_goal_object,
                user=user,
                amount=amount,
                _type=validated_data['type'],
                status=Transaction.TRANSACTION_STATUS_INITIATED
            )
            return TransactionSerializer(instance).data

        except VirtualAccountCreationFailed as ex:
            pass
        except InsufficientBalance as ex:
            pass
        except NotAuthorisedUser as ex:
            pass
        except Exception as ex:
            logger.debug("Can not take deposit right now updating policy")


class TransactionSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    saving_goal = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['pk', 'amount', 'amount_before', 'amount_after', 'type', 'status', 'data', 'created_at',
                  'saving_goal', 'order_id']

    def get_status(self, obj):
        return obj.get_status_display()

    def get_type(self, obj):
        return obj.get_type_display()

    def get_saving_goal(self, obj):
        try:
            return SavingGoalReadSerializer(obj.associated_object).data
        except:
            return


class VirtualAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = VirtualAccount
        fields = ['upi_vpa', 'account_id', 'ifsc_code']