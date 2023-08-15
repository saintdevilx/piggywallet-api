import hashlib
import hmac
import base64
from django.urls import reverse_lazy
from django.utils import timezone

from lib.utils import logger
from mpw import settings


def get_webhook_url(request):
    if settings.DEBUG:
        return F"https://629de08a.ngrok.io/api/{str(reverse_lazy('saving_goal:transaction_webhook_callback'))}"
    else:
        return request.build_absolute_uri('/api/saving/transaction/callback_webhook')


def get_payment_redirect_url(request):
    return request.build_absolute_uri(str(reverse_lazy('saving_goal:payment_redirect')))


def get_payment_redirect_frontend_url(request):
    return F"https://{settings.FRONTEND_DOMAIN}/"


def create_payment_form_data(request, transaction, currency="INR", note="", form_type='popup', payment_modes=''):
    post_data = {
        "appId": settings.CASHFREE_APP_ID,
        "orderId": transaction['pk'],
        "orderAmount": transaction['amount'],
        "orderCurrency": currency,
        "orderNote": note,
        "customerName": request.user.get_full_name(),
        "customerPhone": request.user.get_phone_number(),
        "customerEmail": request.user.get_email(),
        "returnUrl": '',
        "notifyUrl": get_webhook_url(request),
    }
    sorted_keys = sorted(post_data)
    signature_data = ""

    if form_type == 'popup':
        signature_data = "appId=" + post_data['appId'] + "&orderId=" + post_data['orderId'] + "&orderAmount=" + \
               post_data['orderAmount'] + "&returnUrl=" +  post_data['returnUrl'] + "&paymentModes="+\
                         ",".join(payment_modes)
    else:
        for key in sorted_keys:
            signature_data += key + post_data[key];

    message = bytes(signature_data, 'utf-8')
    logger.debug(message)
    # get secret key from your config
    secret = bytes(settings.CASHFREE_SECRET, 'utf-8')
    signature = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest())

    if form_type == 'popup':
        post_data['paymentToken'] = signature
    else:
        post_data['signature'] = signature
        post_data['url'] = settings.PAYMENT_GATEWAY_FORM_URL
    return post_data


def verify_response_signature(request):
    """
    validate the source of request is correct by verifying signature sent along with the response
    only if signature is then only process the request otherwise reject
    :param request:
    :return:
    """
    postData = {
        "orderId": request.data['orderId'],
        "orderAmount": request.data['orderAmount'],
        "referenceId": request.data['referenceId'],
        "txStatus": request.data['txStatus'],
        "paymentMode": request.data['paymentMode'],
        "txMsg": request.data['txMsg'],
        "txTime": request.data['txTime'],
    }

    signatureData = postData["orderId"] + postData["orderAmount"] + postData["referenceId"] + postData["txStatus"] + \
                    postData["paymentMode"] + postData["txMsg"] + postData["txTime"]

    message = bytes(signatureData).encode('utf-8')
    # get secret key from your config
    secret = bytes(settings.CASHFREE_SECRET, 'utf-8')
    signature = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest())
    return signature == request.data['signature']


def current_timestamp_string():
    return str(timezone.now().timestamp()).replace('.', '')