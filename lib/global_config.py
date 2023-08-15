import os

global_config = {
    "userProfilePromptOnBoarding": False,
    "referFriendOptionOnHome": False,
    "enableEarnedReward": True,
    "feedbackOnHome": False,
    "kycOnHome": False,
    "offerOnHome": True,
    "autoDebitEnabled": False,
    "minSavingGoal": 100,
    "minDeductionAmount": 10,
    "minWithdrawAmount": 10,
    "redeemUsingUPI":False
}

REFERRED_REWARD_USER_COUNT = os.environ['REFERRER_USER_COUNT']
REWARD_ON_JOINED = 'REWARD_ON_JOIN' in os.environ


def get_global_config():
    return global_config