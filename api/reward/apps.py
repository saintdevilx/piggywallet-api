from django.apps import AppConfig
import os

class RewardConfig(AppConfig):
    name = 'reward'

ANDROID_PLAYSTORE_APP_LINK = 'https://play.google.com/store/apps/details?id=com.mpw.app&referral=referralCode%3D'
REFERER_MESSAGE = os.environ.get('REFERER_MESSAGE')
REWARD_CASHBACK_MIN = os.environ.get('REWARD_CASHBACK_MIN')
REWARD_CASHBACK_MAX = os.environ.get('REWARD_CASHBACK_MAX')
