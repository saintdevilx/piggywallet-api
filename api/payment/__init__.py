from cashfree_sdk.payouts import Payouts

from lib.cashfree import cashfree_settings

def initPayout():
    Payouts.init(cashfree_settings.CASHFREE_PAYOUT_CLIENT_ID, cashfree_settings.CASHFREE_PAYOUT_CLIENT_SECRET,
                 "TEST" if cashfree_settings.TEST else "PROD", public_key=cashfree_settings.PAYOUT_PUBLIC_KEY)