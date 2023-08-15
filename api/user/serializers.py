from datetime import datetime, date

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer

from api.user.models import UserBankAccount, UserKYCDetail

User = get_user_model()


class UserDetailReadSerializer(ModelSerializer):
    """
    User model object serializer for reading data from an api
    """
    referral_code = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'current_deposit', 'in_progress_goal',
                  'achieved_goal', 'image', 'email_verified', 'kyc_completed', 'referral_code', 'reward_count']

    def get_referral_code(self, obj):
        return obj.get_or_create_referral_code(code=True)


class UserDetailWriteSerializer(ModelSerializer):
    """

    """
    full_name = serializers.CharField(max_length=50)

    class Meta:
        model = User
        fields = ['full_name', 'email']


class UserBankAccountSerializer(ModelSerializer):
    """

    """
    bank_name = serializers.SerializerMethodField()
    bank_logo = serializers.SerializerMethodField()
    account_no = serializers.SerializerMethodField()

    class Meta:
        model = UserBankAccount
        fields = ['pk', 'bank_name', 'account_no', 'bank_logo', 'account_holder_name', 'upi_vpa']

    def get_account_no(self, obj):
        return F'{str(obj.account_no)[:2]}{(len(str(obj.account_no))-6)*"X"}{str(obj.account_no)[-4:]}' if obj.bank \
            else None

    def get_bank_name(self, obj):
        return obj.bank.name if obj.bank else None

    def get_bank_logo(self, obj):
        return obj.bank.logo if obj.bank else None


class UserKYCDetailSerializer(ModelSerializer):
    """"
    """

    gender = serializers.SerializerMethodField()
    adhaar_no = serializers.SerializerMethodField()
    dob = serializers.SerializerMethodField()

    class Meta:
        model = UserKYCDetail
        fields = ['adhaar_no', 'address', 'dob', 'adhaar_image', 'name', 'gender']

    # def get_or_create(self, user, extra=None):
    #     kyc= self.Meta.model.objects.filter(adhaar_no=self.validated_data['adhaar_no']).first()
    #     if kyc:
    #         return (kyc, False)
    #     return (self.save(), True)

    def get_gender(self, obj):
        return obj.get_gender_display()

    def get_adhaar_no(self, obj):
        return F"XXXX XXXX {obj.adhaar_no[:4]}"

    def get_dob(self, obj):
        year = obj.dob.year if isinstance(obj.dob, date) else 'XX'
        return F"XX / XX / {year}"