from mpw import settings

CASHFREE_APP_ID = settings.get_from_environment('CASHFREE_APP_ID')
CASHFREE_SECRET = settings.get_from_environment('CASHFREE_SECRET')
CASHFREE_CAC_CLIENT_ID = settings.get_from_environment('CF_CAC_CLIENT_ID')
CASHFREE_CAC_CLIENT_SECRET = settings.get_from_environment('CF_CAC_CLIENT_SECRET')

CASHFREE_PAYOUT_CLIENT_ID = settings.get_from_environment("CF_PAYOUT_CLIENT_ID")
CASHFREE_PAYOUT_CLIENT_SECRET = settings.get_from_environment("CF_PAYOUT_CLIENT_SECRET")

PRODUCTION = not settings.DEBUG
TEST = settings.DEBUG
CASHFREE_PG_NOTIFY_URL = F'https://{settings.BACKEND_DOMAIN}/api/saving/transaction/callback_webhook'
CASHFREE_RECURRING_API_URL = settings.get_from_environment("CF_RECURRING_API_URL", fail_silently=True)
PAYOUT_PUBLIC_KEY = settings.get_from_environment("CF_PUBLIC_KEY")