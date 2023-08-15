import json
import secrets
from datetime import timedelta

import requests
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils import timezone

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import ugettext_lazy as _
import uuid

from api.fcm_django.models import FCMDevice
from api.payment import initPayout
from api.user.exceptions import EmailAlreadyExists, VerificationLinkExpired
from api.user.tasks import send_verification_email
from lib.cashfree.autocollect import AutoCollect
from lib.core.models import BaseModel
from lib.global_config import REFERRED_REWARD_USER_COUNT, REWARD_ON_JOINED
from lib.utils import logger, create_presigned_post, js_timestamp_date_to_utc_datetime, get_jwt_token, verify_jwt_token
from mpw import settings
from cashfree_sdk.payouts.beneficiary import Beneficiary


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, phone_number, email,
                     password,device_id, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(
            username=username, email=email, phone_number=phone_number,
            **extra_fields
        )
        user.set_password(password)
        logger.debug(('EXTEA FIELDS', device_id))
        user.device_id = device_id
        user.save(using=self._db)
        return user

    def create_user(self, username, phone_number,
                    email=None, password=None, device_id=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, phone_number, email, password,device_id,
                                 **extra_fields)

    def create_superuser(self, username, phone_number, email, password,
                         **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, phone_number, email, password,
                                 **extra_fields)


class User(AbstractUser):
    uid = models.CharField(max_length=100, help_text='to verify user from firebase phone auth')
    phone_number = PhoneNumberField(unique=True)
    current_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    email_verified = models.BooleanField(default=False)
    image = models.CharField(max_length=500, default='', blank=True)
    achieved_goal = models.IntegerField(default=0)
    in_progress_goal = models.IntegerField(default=0)
    kyc_completed = models.BooleanField(default=False)

    referral_code = models.CharField(max_length=50, null=True)
    referral_link = models.CharField(max_length=100, blank=True, null=True)
    reward_count = models.SmallIntegerField(default=0)

    objects = UserManager()

    def __str__(self):
        return F"{self.get_full_name()}"

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def create_short_link(self, code):
        data = {'dynamicLinkInfo': {'domainUriPrefix': 'mpwg.page.link',
                                    'link': F'https://mypiggywallet.com?refCode={code}',
                                    'androidInfo': {'androidPackageName': 'com.mpw.app'},
                                    'analyticsInfo': {'googlePlayAnalytics': {'utmSource': F'invite_{code}',
                                                                              'utmCampaign': 'referral'}
                                                      }
                                    },
                'suffix': {'option': 'SHORT'}
                }
        response = requests.post(settings.FIREBASE_DYNAMIC_LINK_API_URL, data=json.dumps(data))
        if response.ok:
            return response.json().get('shortLink')
        else:
            print('error...', response.json())

    def get_or_create_referral_code(self, code=False):
        if self.referral_code and self.referral_link:
            return self.referral_link if not code else self.referral_code
        else:
            for i in range(10):
                code = secrets.token_hex(3) if not self.referral_code else self.referral_code
                if self.referral_code  or not User.objects.filter(referral_code__iexact=code).exists():
                    self.referral_code = code
                    self.referral_link = self.create_short_link(code)
                    self.save(update_fields=['referral_code', 'referral_link'])
                    return self.referral_link if not code else self.referral_code

    def get_virtual_account(self):
        try:
            return self.virtualaccount
        except:
            return

    def create_virtual_account(self):
        try:
            response = AutoCollect().create_virtual_account(self)
            logger.debug(response)
            VirtualAccount.objects.create(user=self,account_vpa_id=response['vpa'])
        except Exception as ex:
            logger.exception('Create virtual account exception')
            pass

    def set_current_amount(self, amount):
        self.current_deposit = amount
        self.save()

    def get_phone_number(self):
        return str(self.phone_number)

    def get_email(self):
        return self.email

    def get_image_url(self):
        return self.image.url if self.image else None

    def set_image(self, image):
        self.image = image.get_file_url()
        self.save()

    def update_details_via_google(self, user_data):
        self.update_details(user_data, email_verified=True, picture=True)

    def update_details(self, user_data, email_verified=False, picture=False):
        update_fields = ['first_name', 'last_name', 'email', 'email_verified']
        if user_data.get('email') and User.objects.filter(email__iexact=user_data['email']).exclude(pk=self.pk).exists():
            raise EmailAlreadyExists(" Email already exist with other account")
        self.first_name = user_data['name'].split()[:1][0]
        self.last_name = " ".join(user_data['name'].split()[1:])
        if user_data.get('email'):
            self.email = user_data.get('email')

        if email_verified:
            self.email_verified=user_data['email_verified']
            update_fields.append('email_verified')
        if picture:
            self.image = user_data['picture']
            update_fields.append('image')

        self.save(update_fields=update_fields)
        return self

    def get_or_create_kyc(self, data, share_code, xml_data):
        try:
            kyc = UserKYCDetail.objects.get(user_id=self.id)
            return kyc, False
        except UserKYCDetail.DoesNotExist as ex:
            extra_data = json.dumps({'share_code': share_code, 'xml_data':xml_data})
            return UserKYCDetail.create(user=self, name=data['name'], adhaar_no=data['reference_id'], adhaar_image=data['image'],
                                        dob=data['dob'], address=data['address'], gender=data['gender'].lower(),
                                        phone=data['phone'], email=data['email'], extra=extra_data)

    def set_kyc_approved(self):
        self.kyc_completed = True
        self.save()

    def get_email_verification_token(self):
        payload = {
            'pk': self.pk,
            'email': self.email,
            'ttl': (timezone.now() + timedelta(hours=72)).strftime('%s')
        }
        return get_jwt_token(payload)

    def get_email_verification_link(self):
        jwt_token = self.get_email_verification_token()
        path = reverse('user:email_verification_link', kwargs={'jwt_token': jwt_token})
        return F"https://{settings.SITE_DOMAIN}/{path}"

    @staticmethod
    def verify_email_verification_token(jwt_token):
        payload = verify_jwt_token(jwt_token)
        logger.debug((payload, timezone.now().strftime('%s')))
        if int(payload.get('ttl')) < int(timezone.now().strftime('%s')):
            raise VerificationLinkExpired('Verification link is not valid for 72 hours')
        user = User.objects.get(pk=payload['pk'])
        user.email_verified = True
        user.save(update_fields=('email','email_verified'))
        return user

    def send_verification_email(self):
        context = {
            'first_name': self.first_name,
            'confirmation_link': self.get_email_verification_link()
        }
        send_verification_email.delay(self.email, 'send_email_verification_link', context=context)

    def sync_reward_count(self):
        from api.reward.models import Reward
        self.reward_count = self.reward_set.filter(status=Reward.REWARD_STATUS_UNOPENED).count()
        self.save()


class VirtualAccount(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=50, null=True)
    account_vpa_id = models.CharField(max_length=50, null=True)

    def __str__(self):
        return F"{self.account_id or ''}{self.account_vpa_id or ''}"


class Bank(models.Model):
    PUBLIC_BANK = 0
    PRIVATE_BANK = 1
    FOREIGN_BANK = 2
    COOPERATIVE_BANK = 3
    RURAL_BANK = 4
    PAYMENT_BANK = 5

    BANK_TYPE_CHOICES = (
        (PUBLIC_BANK,'PUBLIC'), (PRIVATE_BANK,'PRIVATE'), (FOREIGN_BANK, 'FOREIGN'),(COOPERATIVE_BANK, "COOPERATIVE"),
        (RURAL_BANK, 'RURAL'), (PAYMENT_BANK, 'PAYMENT')
    )
    name = models.CharField(max_length=300)
    type = models.SmallIntegerField(choices=BANK_TYPE_CHOICES, default=PUBLIC_BANK)
    logo = models.CharField(max_length=500, default='')

    def __str__(self):
        return self.name


class UserBankAccount(BaseModel):
    """
    User Bank account details for making transaction
    Pk will be the beneficiary_id for cashfree payout
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, null=True)
    account_no = models.CharField(max_length=50, null=True)
    account_holder_name = models.CharField(max_length=100, null=True)
    ifsc_code = models.CharField(max_length=20, null=True)
    upi_vpa = models.CharField(max_length=100, null=True)

    def __str__(self):
        return F"{self.user} {self.bank}"

    def remove_bank_account(self, user):
        if self.user == user:
            self.delete()
            return True

    @classmethod
    def get_user_account(cls, user):
        return cls.objects.filter(user=user).prefetch_related('bank')

    @classmethod
    def create_or_update(cls, user, data):
        if not data['upi_vpa']:
            bank, status = Bank.objects.get_or_create(name__iexact=data['bank_name'].lower().strip(), defaults={
                'name': data['bank_name'].lower().strip()
            })
            logger.debug((data, bank, status))
            bank_acnt, status = cls.objects.get_or_create(user=user, account_no=data['account_no'], bank=bank,
                                             defaults=dict(account_holder_name=data['account_holder_name'],
                                                           ifsc_code=data['ifsc_code']))
        else:
            bank_acnt, status = cls.objects.get_or_create(user=user, upi_vpa=data['upi_vpa'])

        if status:
            bank_acnt.add_beneficiary()
        return bank_acnt,status

    def add_beneficiary(self):
        kwargs = dict(beneId=str(self.pk).replace('-', ''),
                      name=self.user.get_full_name(), email=self.user.get_email(),
                      phone=self.user.phone_number.national_number, address1="ABC Street")
        if not self.upi_vpa:
            kwargs.update(dict(bankAccount=str(self.account_no), ifsc=str(self.ifsc_code)))
        else:
            kwargs.update({'vpa':self.upi_vpa})
        benef_add = Beneficiary.add(**kwargs)
        return benef_add


class UserPaymentDetail(models.Model):
    pass


class UserKYCDetail(BaseModel):
    MALE = 'm'
    FEMALE = 'f'
    OTHER = 'o'
    GENDER_CHOICES = (
        (MALE, 'MALE'),
        (FEMALE, 'FEMALE'),
        (OTHER, 'OTHER')
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='')
    gender =models.CharField(max_length=1, choices=GENDER_CHOICES, null=True)
    pan_no = models.CharField(max_length=20, null=True, blank=True)
    pan_image = models.CharField(max_length=500, null=True, blank=True)
    adhaar_no = models.CharField(max_length=50)
    adhaar_image = models.TextField(null=True, blank=True)
    user_photo = models.CharField(max_length=500, null=True, blank=True)
    extra = models.TextField(blank=True, default="")
    address = models.CharField(blank=True, default="", max_length=300)
    dob = models.DateField(null=True, blank=True)
    phone  = models.CharField(max_length=20, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return "%s"%self.adhaar_no

    @staticmethod
    def create(user, name, adhaar_no, adhaar_image, gender, dob, address, extra=None, phone=None, email=None):
        gender = gender if gender.lower() in (UserKYCDetail.MALE, UserKYCDetail.FEMALE) else UserKYCDetail.OTHER
        kyc, status = UserKYCDetail.objects.get_or_create(user=user,
                                                          defaults=dict(name=name, adhaar_no=adhaar_no,
                                                                        adhaar_image=adhaar_image, gender=gender,
                                                                        dob=dob, address=address, extra=extra,
                                                                        phone=phone, email=email))
        if status:
            user.set_kyc_approved()
        return kyc, status


class UploadFile(BaseModel):
    path = models.CharField(max_length=500)
    content_type = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    public = models.BooleanField(default=True)

    def __str__(self):
        return self.path

    @staticmethod
    def create(path, user, content_type='image', acl='public-read'):
        path = F"path/{uuid.uuid4().hex}.png"
        content = create_presigned_post(settings.AWS_STORAGE_BUCKET_NAME, path,
                              fields={'acl': acl}, conditions=[{"acl": acl}])
        file = UploadFile.objects.create(path=path, content_type=content_type, user=user)
        content['file_id'] = file.pk
        return content

    def get_file_url(self):
        return F"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{self.path}"


class UserContact(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contact_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    updated_at = models.DateField(null=True, default=None, blank=True)

    class Meta:
        unique_together = ('user', 'contact_number',)

    def __str__(self):
        return F"{self.contact_name}-{self.contact_number}"

    @staticmethod
    def create(contact_list, user_id):
        _contact_list = []
        current_time = timezone.now()
        for contact in contact_list:
            _contact_list.append(UserContact(user_id=user_id, contact_name=contact['displayName'],
                                             contact_number=contact['phoneNumbers'][0]['normalizedNumber'],
                                             updated_at=current_time))
        UserContact.objects.bulk_create(_contact_list, ignore_conflicts=True)


class UserSMS(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    sender = models.CharField(max_length=100)
    received_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'sender',)

    def __str__(self):
        return F"{self.sender} - {self.text[:15]}"

    @staticmethod
    def create(bulk_sms_list, user_id):
        BATCH_SIZE = 500
        for index in range(0, len(bulk_sms_list), BATCH_SIZE):
            _sms_list = []
            for sms in bulk_sms_list[index: index + BATCH_SIZE - 1]:
                _sms_list += [UserSMS(user_id=user_id, text=sms['body'], sender=sms['address'],
                                      received_date=js_timestamp_date_to_utc_datetime(sms['date']))]
            if _sms_list:
                UserSMS.objects.bulk_create(_sms_list, ignore_conflicts=True)


class ReferredUser(BaseModel):
    referrer = models.ForeignKey(User, related_name='referer', on_delete=models.CASCADE)
    referee = models.ForeignKey(User, related_name='referee', on_delete=models.CASCADE)
    device_id = models.CharField(max_length=100, blank=True, null=True)

    @classmethod
    def create(cls, user, referrer_code, device_id):
        print('referrer_code', referrer_code, 'creating referrer....')
        if referrer_code and device_id:
            referrer = User.objects.filter(referral_code=referrer_code).first()
            logger.debug(("refeerer found...", referrer))
            if referrer:
                return cls.objects.get_or_create(device_id=device_id, defaults={"referrer": referrer, "referee": user})


# ===================================================================================
# signals ......

@receiver(post_save, sender=User)
def post_user_save(sender, instance, **kwargs):
    logger.debug((sender, instance, kwargs, kwargs.get('update_fields') and 'email_verified' in kwargs.get('update_fields',[])))
    if not instance.email_verified and kwargs.get('update_fields') and 'email' in kwargs.get('update_fields'):
        context = {
            'first_name': instance.first_name,
            'confirmation_link': instance.get_email_verification_link()
        }
        send_verification_email.delay(instance.email, 'send_email_verification_link', context=context)


@receiver(post_save, sender=ReferredUser)
def post_referred_user_save(sender, instance, **kwargs):
    if kwargs.get('created'):
        logger.debug((sender, instance, kwargs, "====> referred_user"))
        from api.reward.models import Reward
        count = ReferredUser.objects.filter(referrer=instance.referrer).count()
        if count % int(REFERRED_REWARD_USER_COUNT) == 0:
            Reward.add_reward(instance.referrer, earned_for='Referring user', type=Reward.REWARD_TYPE_CASH_BACK,
                              status=Reward.REWARD_STATUS_UNOPENED)


@receiver(post_save, sender=User)
def post_user_create(sender, instance, **kwargs):
    if kwargs.get('created'):
        logger.debug(('user created.....', kwargs, 'device_id', getattr(instance, 'device_id', None)))
        device_id = getattr(instance, 'device_id', None)
        from api.reward.models import Reward
        logger.debug(('DEVICE EXIST>>>>', FCMDevice.objects.filter(device_id=device_id).exists()))
        if REWARD_ON_JOINED and not FCMDevice.objects.filter(device_id=device_id).exists():
            Reward.add_reward(instance, earned_for='Joining', type=Reward.REWARD_TYPE_CASH_BACK,
                              status=Reward.REWARD_STATUS_UNOPENED)
