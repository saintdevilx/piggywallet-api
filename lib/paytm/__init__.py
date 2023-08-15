# For Staging
import logging

from paytmpg import LibraryConstants, MerchantProperty

from mpw import settings

environment = LibraryConstants.PRODUCTION_ENVIRONMENT

# For Production
# environment = LibraryConstants.PRODUCTION_ENVIRONMENT

# Find your mid, key, website in your Paytm Dashboard at https://dashboard.paytm.com/next/apikeys
mid = settings.PAYTM_MERCHANT_ID
key = settings.PAYTM_MERCHANT_KEY
website = settings.PAYTM_WEBSITE
client_id = None
#MerchantProperty.set_callback_url_default('https://enuk9sn31xwc.x.pipedream.net/')
#MerchantProperty.set_callback_url('https://enuk9sn31xwc.x.pipedream.net/')
MerchantProperty.initialize(environment, mid, key, client_id, website)
 # If you want to add log file to your project, use below code
# file_path = '/path/log/file.log'
# handler = logging(file_path)
# formatter = logging.Formatter("%(name)s: %(levelname)s: %(message)s")
# handler.setFormatter(formatter)
# MerchantProperty.set_log_handler(handler)
# MerchantProperty.set_logging_disable(True)
# MerchantProperty.set_logging_level(logging.DEBUG)
logger = logging.getLogger("Paytm")
log_handler = logging.StreamHandler()
frmt = {'fmt': "[%(levelname)s(%(name)s): %(asctime)s] \nPath: %(pathname)s |Function: %(funcName)s |Line: %(lineno)s \nMessage: %(message)s \n",
 'datefmt': "%d/%b/%Y %H:%M:%S"}
formatter = logging.Formatter(**frmt)

log_handler.setFormatter(formatter)
MerchantProperty.set_log_handler(log_handler)
MerchantProperty.set_logging_disable(False)
MerchantProperty.set_logging_level(logging.DEBUG)