#
#
# https://docs.cashfree.com/docs/cac/
import base64
import hashlib
import hmac
import json
from urllib import parse

import requests
from cashfree_sdk.exceptions.exceptions import ModuleNotInitiatedError, InvalidaWebHookPayloadTypeError

from lib.cashfree import cashfree_settings
from lib.cashfree.exceptions import InvalidCredential, InvalidAuthToken, RequestFailed
from lib.utils import logger


class CFResponse:
    status = None
    message = ""
    subCode = ""
    data = {}
    _response = None

    def set_response(self, response):
        value = response.json()
        for key in value.keys():
            setattr(self, key, value[key])
        self._response = response
        return self


class VirtualAccount:
    account_id = None
    account_vpa_id = None
    name = None
    phone = None
    email = None
    notif_group = None
    remitter_account = None
    remitter_ifsc = None
    create_multiple = None

    def validate(self):
        assert self.account_id or self.account_vpa_id
        assert self.name
        assert self.phone
        assert self.email

    def __init__(self, **kwargs):
        self.account_vpa_id = kwargs.get('account_id')
        self.account_id = kwargs.get('account_id')
        logger.debug(kwargs)
        self.name = kwargs['name'] if kwargs else None
        self.email = kwargs['email'] if kwargs else None
        self.phone = kwargs['phone'] if kwargs else None
        self.notif_group = kwargs.get('notif_group', '')
        self.remitter_account = kwargs.get('remitter_account', '')
        self.remitter_ifsc = kwargs.get('remitter_isfc', '')
        self.create_multiple = 0

    def set_user_details(self, user):
        self.name = user.get_full_name()
        self.email = user.get_email()
        self.account_vpa_id = F"{user.first_name[:10]}{user.phone_number.national_number}".lower()
        # self.account_id = F"{user.first_name[:8]}".lower()
        self.phone = str(user.phone_number.national_number)
        return self

    def to_dict(self):
        data = dict(virtualVpaId=self.account_vpa_id, vAccountId=self.account_id.upper() if self.account_id else None,
                    name=self.name, phone=str(self.phone), email=self.email, notifGroup=self.notif_group or 'DEFAULT')
        return {k: v for k, v in data.items() if data[k] is not None}


class AutoCollect:
    '''

    '''
    
    TEST_URL = "https://cac-gamma.cashfree.com"
    PRODUCTION_URL = "https://cac-api.cashfree.com"
    token = None

    def __init__(self):
        self.authenticate()

    def send_request(self, method, url_path, headers={}, payload={}):
        if self.token:
            headers.update({'Authorization': F"Bearer {self.token}"})
        url = F"{self.TEST_URL}{url_path}" if cashfree_settings.TEST else F"{self.PRODUCTION_URL}{url_path}"
        logger.debug(('send_request token', url, headers, payload))
        _response = getattr(requests, method.lower())(url, headers=headers, data=payload)
        logger.debug(('payload', payload, 'response', _response.json(), url))
        if not _response.ok:
            raise RequestFailed(_response)
        response = CFResponse().set_response(_response)
        return response

    def get_auth_token(self, response):
        return response.data['token']

    def authenticate(self):
        headers = {
            "X-Client-Id": cashfree_settings.CASHFREE_CAC_CLIENT_ID,
            "X-Client-Secret": cashfree_settings.CASHFREE_CAC_CLIENT_SECRET
        }
        response = self.send_request('post', '/cac/v1/authorize', headers=headers)
        # logger.debug((response, response._response.__dict__))
        if response._response.ok:
            if response.subCode == "200":
                self.token = self.get_auth_token(response)
                return response
            else:
                raise InvalidCredential(response.message)
        else:
            raise InvalidCredential(response.message)

    @staticmethod
    def verify_token(self, token):
        headers = {'Authorization': F"Bearer {token}"}
        response = self.send_request('post', '/cac/v1/verifyToken', payload={}, headers=headers)
        if response.subCode == "403":
            raise InvalidAuthToken
        return response

    def create_virtual_account(self, user):
        payload = VirtualAccount().set_user_details(user).to_dict()
        logger.debug((json.dumps(payload), 'payload json'))
        try:
            response = self.send_request("post", "/cac/v1/createVA", payload=json.dumps(payload))
        except:
            return
        payload.update(response.data)
        return payload

    def update_virtual_account(self):
        pass

    def change_virtual_account_status(self, vaccount, status, account_or_vpa_id=None):
        payload = {'virtual_vpa_id': vaccount.virtual_vpa_id, "status":status}
        return self.send_request('post', F'/cac/v1/changeVAStatus', payload=payload)

    def get_recent_payments(self, start_date, end_date, max_return, last_return_id=None, account_id=None):
        payload = {'startDate': start_date, 'endDate':end_date, 'maxReturn':max_return, 'lastReturnId':last_return_id}
        url = F"/cac/v1/payments"
        if account_id:
            url = F"{url}/{account_id}"
        return self.send_request('get', url, payload=payload)

    def get_recent_payments_for_va(self, start_date, end_date, max_return, account_id, last_return_id=None):
        return self.get_recent_payments(start_date, end_date, max_return, account_id, last_return_id=last_return_id)

    def get_recent_payments_for_vpa(self, start_date, end_date, max_return, account_id, last_return_id=None):
        return self.get_recent_payments(start_date, end_date, max_return, account_id, last_return_id=last_return_id)

    def get_rejected_payments(self, reject_id):
        return self.send_request('post', F'/cac/v1/rejectedPayment/{reject_id}')

    def get_settlement_details(self, settlement_utr=None,settlement_id=None):
        url_path = F'/cac/v1/getSettlementDetails'
        if settlement_utr:
            url_path += F"settlementUtr={settlement_utr}"
        elif settlement_id:
            url_path += F"settlementId={settlement_id}"
        return self.send_request('post', url_path)

    def get_virtual_account_details(self):
        pass
    
    def search_transaction_by_utr(self):
        ''' This search is limited to last 48 hours by default. You can search a different time range using
        startDate and
        endDate query params in the GET url. However, this range can not be greater than 30 days.'''
        pass

    @classmethod
    def verify_webhook(cls, webhook_data, payload_type='FORM'):
        if not payload_type or payload_type not in ('FORM', 'JSON'):
            raise InvalidaWebHookPayloadTypeError()

        data = {}

        if payload_type == 'FORM':
            data = dict((k, v if len(v) > 1 else v[0])
                        for k, v in parse.parse_qs(webhook_data).items())
            if len(data) == 0 or 'signature' not in data:
                return False
        else:
            data = json.loads(webhook_data)
            if len(data) == 0 or 'signature' not in data:
                return False

        logger.debug(data)
        return cls.__verify_webhook(data)

    @classmethod
    def __verify_webhook(cls, data):
        if not cashfree_settings.CASHFREE_CAC_CLIENT_ID:
            raise ModuleNotInitiatedError()

        key = cashfree_settings.CASHFREE_CAC_CLIENT_SECRET
        signature = data['signature']
        sorted_data_dict = {key: data[key] for key in sorted(data) if key != 'signature'}
        val_str = "".join(str(val) for val in sorted_data_dict.values())

        hash_val = hmac.new(key.encode(), val_str.encode(), hashlib.sha256).digest()

        gen_signature = base64.b64encode(hash_val)
        if gen_signature == signature.encode():
            return True

        return False
