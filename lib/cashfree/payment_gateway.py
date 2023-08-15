import json
from lib.cashfree import cashfree_settings
import requests
from lib.cashfree.exceptions import RequestFailed
from lib.utils import logger
import hashlib
import hmac
import base64


class UPIBase:
    def get_data(self):
        fields = []
        for field in self.__dir__():
            if isinstance(getattr(self, field), Field):
                fields.append((field, getattr(self, field).value))
        return fields

    def json(self):
        return json.dumps(dict(self.get_data()))


class BaseResponse:
    def set_response(self, response):
        try:
            value = response.json() if hasattr(response, 'json') else response
            for key in value.keys():
                setattr(self, key, value[key])
            self._response = response
            return self
        except:
            logger.exception("error..")

    def verify(self):
        if hasattr(self,'signature'):
            logger.debug(getattr(self,'signature'))
            return getattr(self,'signature') == generate_signature(dict(getattr(self,'get_data')()))
        else:
            return False


def generate_signature(post_data):
    sorted_keys = sorted(post_data)
    signature_data = ""
    for key in sorted_keys:
        if post_data[key] and key != 'signature':
            signature_data += key + str(post_data[key])
    logger.debug(signature_data)

    message = bytes(signature_data, encoding='utf8')
    # get secret key from your config
    secret = bytes(cashfree_settings.CASHFREE_SECRET, encoding='utf8')
    signature = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest())
    return str(signature, 'utf8')


class Field:
    value = None

    def __init__(self, value=None):
        self.value = value

    def __set__(self, instance, value):
        self.value = value

    def __repr__(self):
        return self.value


class UPIRequest(UPIBase):
    appId = Field(cashfree_settings.CASHFREE_APP_ID)
    #secretKey = Field(cashfree_settings.CASHFREE_SECRET)
    orderId = Field()
    orderAmount = Field()
    orderCurrency = Field("INR")
    orderNote = Field()
    customerName = Field()
    customerEmail = Field()
    customerPhone = Field()
    returnUrl = Field()
    notifyUrl = Field(cashfree_settings.CASHFREE_PG_NOTIFY_URL)
    signature = Field()
    paymentOption = Field('upi')
    responseType = Field("json")
    upiMode = Field('link')
    upi_vpa = Field('success@upi')

    def prepare_request(self):
        self.signature = generate_signature(dict(self.get_data()))

    def set_data(self, data):
        """

        :param transaction: saving_goal.models.Transaction Object
        :return:
        """
        self.orderId = data['order_id']
        self.orderAmount = data['amount']
        self.customerName = data['full_name']
        self.customerPhone = data['phone']
        self.customerEmail = data['email']
        self.upi_vpa = data.get('upi_vpa')
        # generate the signature after setting the data
        self.prepare_request()


class UPIResponse(BaseResponse, UPIBase):
    status = Field()
    message = Field()
    qr = Field()
    link = Field()
    referenceId = Field()
    orderIid = Field()
    _response = None


class PaymentDetails:
    paymentMode = Field()
    bankName = Field()
    cardNumber = Field()
    cardCountry = Field()
    cardScheme = Field()
    utr = Field()


class UPIOrderStatus:
    PAID = "PAID"
    ACTIVE = "ACTIVE"


class UPIOrderStatusResponse(UPIBase, BaseResponse):
    orderStatus = Field()
    orderId = Field()  # Order id for which transaction has been processed. Ex: GZ-212”
    orderAmount = Field()  # Amount of the order. Ex: 256.00
    referenceId = Field()  # transaction reference id, if payment has been attempted
    txStatus = Field()  # transaction status, if a payment has been attempted
    paymentMode = Field()  # payment mode of transaction, if payment has been attempted
    txMsg = Field()  # transaction message, if payment has been attempted
    txTime = Field()  # transaction time, if payment has been attempted
    signature = Field()  # response signature
    paymentDetails = PaymentDetails()
    # paymentDetails.paymentMode	payment mode of transaction, if payment has been attempted
    # paymentDetails.bankName	Name of the bank if payment has been attempted (only incase of Netbanking)
    # paymentDetails.cardNumber	Masked card number if payment has been attempted(only in case of Debit & Credit Cards)
    # paymentDetails.cardCountry	Country code of the card if payment has been attempted (only in case of Debit & Credit Cards)
    # paymentDetails.cardScheme	Scheme of the card (eg:VISA) if payment has been attempted (only in case of Debit & Credit Cards)
    # paymentDetails.utr	UTR of UPI transaction(only in case of UPI)


class UPICallbackResponse(BaseResponse, UPIBase):
    orderId = Field()  # Order id for which transaction has been processed. Ex: GZ-212”
    orderAmount = Field()  # Amount of the order. Ex: 256.00
    referenceId = Field()  # transaction reference id, if payment has been attempted
    txStatus = Field()  # transaction status, if a payment has been attempted
    paymentMode = Field()  # payment mode of transaction, if payment has been attempted
    txMsg = Field()  # transaction message, if payment has been attempted
    txTime = Field()  # transaction time, if payment has been attempted
    signature = Field()  # response signature

    def get_signature(self):
        postData = dict(self.get_data())
        signatureData = postData["orderId"] + postData["orderAmount"] + postData["referenceId"] + postData["txStatus"] + \
                        postData["paymentMode"] + postData["txMsg"] + postData["txTime"]

        message = bytes(signatureData, encoding='utf-8')
        # get secret key from your config
        secret = bytes(cashfree_settings.CASHFREE_SECRET,encoding='utf-8')
        signature = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest())
        return str(signature, 'utf8')

    def verify(self):
        return str(self.signature) == str(self.get_signature())


class UPIGateway:
    endpoint = "https://test.cashfree.com/" if cashfree_settings.TEST and not cashfree_settings.PRODUCTION \
        else "https://www.cashfree.com/"

    def send_request(self, method, url_path, headers=None, payload=None, files=None, serializer=UPIResponse):
        url = F"{self.endpoint}{url_path}"
        logger.debug(('send_request token', url, headers))
        logger.debug(files)
        _response = getattr(requests, method.lower())(url, headers=headers, data=payload, files=files)
        logger.debug(_response.content)
        if not _response.ok:
            raise RequestFailed(_response)
        response = serializer().set_response(_response)
        logger.debug(response)
        return response

    def get_order_status(self, order_id):
        url = F"api/v2/orders/{order_id}/status"
        headers = {
            'X-Client-Secret': cashfree_settings.CASHFREE_SECRET,
            'X-Client-Id': cashfree_settings.CASHFREE_APP_ID
        }
        return self.send_request('get', url, headers=headers, serializer=UPIOrderStatusResponse)
    
    def submit(self, data):
        req = UPIRequest()
        req.set_data(data)
        payload = [(k, (None, v)) for k,v in dict(req.get_data()).items() if v]
        url = F"{'billpay/' if not cashfree_settings.PRODUCTION and cashfree_settings.TEST else ''}checkout/post/submit"
        return self.send_request('post', url_path=url, files=payload)
