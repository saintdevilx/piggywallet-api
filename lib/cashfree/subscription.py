import json

import requests

from lib.utils import logger
from lib.cashfree import cashfree_settings as settings


class CashFreeSubscription:
    """
    Cashfree Subscription enables you to manage recurring payments. You can easily create and manage subscriptions and
    charge your customers automatically as per the plans defined by you. Whatever be your business model, you can use
    Cashfree as your building block. The Subscription service is available through the Dashboard and API.
    To get started with Subscription you need to follow the below steps -
       1. Create plans
       2. Create subscriptions and Authorize
       3. Manage subscriptions
    """
    API_URL = settings.CASHFREE_RECURRING_API_URL
    HEADERS = {'X-Client-Id': settings.CASHFREE_APP_ID, 'X-Client-Secret': settings.CASHFREE_SECRET,
               'content-type': 'application/json'}

    def __init__(self):
        pass

    def _get_interval_type(self, interval_type):
        return {1: 'day', 7: "week", 30: "month"}.get(interval_type)

    def _get(self, path, data={}):
        return requests.get(F"{self.API_URL}{path}", headers=self.HEADERS, params=data)

    def _post(self, path, data):
        return requests.post(F"{self.API_URL}{path}", headers=self.HEADERS, data=json.dumps(data))

    def get_redirect_url(self):
        return F"http://{settings.FRONTEND_DOMAIN}/api/payment/subscription-callback"

    def create(self, plan_id, plan_name, amount, interval_type, max_cycle=None,
               description='', max_amount=20000, type='PERIODIC', intervals=1):
        """
        :param plan_id:	Unique identifier for the plan (Alphanumeric)

        :param plan_name:	Specify name for easy reference (Alphanumeric)

        :param type:	The type can be PERIODIC or ON_DEMAND. For more details refer to Appendix 1 for description
        (Alphanumeric)

        :param max_cycles:	(Optional)	Maximum number of debits set for the plan. The subscription will automatically
        change to COMPLETED status once this limit is reached (Numeric)

        :param  amount:	(Optional)	The amount to be charged for PERIODIC plan (Numeric)

        :param max_amount: (Optional)	The maximum amount to be charged for ON_DEMAND plan (Numeric)

        :param interval_type: (Optional)	The type of interval for a PERIODIC plan like daily, weekly, monthly, yearly
        (Alphanumeric)

        :param intervals:(Optional)	Number of intervals of intervalType between every subscription payment.
            For example for charging customer bi weekly use intervalType as “week” and intervals as 2.
            Required for PERIODIC plan (Numeric)
        :param description:	(Optional)	A brief note for the plan (Alphanumeric)

        https://docs.cashfree.com/docs/sbc/guide/#create-plan
        """
        logger.debug({
            'planId': plan_id, 'planName': plan_name, 'type': type, 'amount': amount, 'maxAmount': max_amount,
            'intervalType': self._get_interval_type(interval_type), 'intervals': intervals, 'maxCycles':max_cycle
        })
        return self._post('/api/v2/subscription-plans', {
            'planId': plan_id, 'planName': plan_name, 'type': type, 'amount': amount, 'maxAmount': max_amount,
            'intervalType': self._get_interval_type(interval_type), 'intervals': intervals, 'maxCycles':max_cycle
        })

    def subscribe(self, subscription_id, plan_id, customer_name, customer_email, customer_phone,
                  expires_on, subscription_note="", first_charge_delay=0, auth_amount=1):
        """
        :param subscription_id:	A unique id generated for subscription (Alphanumeric)

        :param plan_id:	Id of a valid plan created earlier (Alphanumeric)

        :param customer_name:(Optional)	Name of the customer (Alphanumeric)

        :param customer_email: Email of the customer (Alphanumeric)

        :param customer_phone: Contact number of the customer (Numeric)

        :param first_charge_delay: (Optional) Number of Days after which the first debit for subscription will occur.
            Applicable for periodic subscriptions only (Numeric)

        :param auth_amount:	(Optional) The amount that will be charged to authenticate the payment.
            The default amount is Re. 1 (Numeric)

        :param expires_on:	The last date till which the subscription stands valid.
            The status of subscription will be COMPLETED. Default value is 2 years from date of subscription creation.
            Format is “yyyy-mm-dd hr:min:sec” (Alphanumeric)

        :param subscription_note: (Optional) A brief note about the subscription (Alphanumeric)

        :param return_url: A valid url to which customer will be redirected to after the subscription is done.
        Refer “Payment Response” section (Alphanumeric)
        """
        try:
            logger.debug({
                'subscriptionId': subscription_id,
                'planId': plan_id,
                'customerName': customer_name,
                'customerEmail': customer_email,
                'customerPhone': customer_phone,
                'firstChargeDelay': first_charge_delay,
                'authAmount': auth_amount,
                'expiresOn': expires_on,
                'returnUrl': self.get_redirect_url(),
                'subscriptionNote': subscription_note
            })
            return self._post('/api/v2/subscriptions', {
                'subscriptionId': subscription_id,
                'planId': plan_id,
                'customerName': customer_name,
                'customerEmail': customer_email,
                'customerPhone': customer_phone,
                'firstChargeDelay': first_charge_delay,
                'authAmount': auth_amount,
                'expiresOn': expires_on,
                'returnUrl': self.get_redirect_url(),
                'subscriptionNote': subscription_note
            }).json()
        except Exception as ex:
            logger.exception(ex)

    def unsubscribe(self, subscription_id):
        try:
            response = self._post(F'/api/v2/subscription/{subscription_id}/cancel',{})
            logger.debug(response.content)
            return response.json()
        except Exception as ex:
            logger.exception(ex)
            pass

    def charge_on_demand(self):
        pass

    def get_subscriptions(self):
        pass

    def get_subscription_details(self, reference_id):
        try:
            return self._get(F'/api/v2/subscriptions/{reference_id}').json()
        except Exception as ex:
            logger.exception(ex)

    def get_subscription_payment_details(self):
        pass
