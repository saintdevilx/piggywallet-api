from cashfree_sdk.payouts.__authorize_creds import authorize
from cashfree_sdk.payouts.cashgram import Cashgram
from cashfree_sdk.payouts.transfers import RequestTransfer
from django.utils import timezone

from lib.cashfree.autocollect import CFResponse

from cashfree_sdk.payouts import Payouts, __request

from lib.cashfree import cashfree_settings


def init_payout():
    Payouts.init(cashfree_settings.CASHFREE_PAYOUT_CLIENT_ID, cashfree_settings.CASHFREE_PAYOUT_CLIENT_SECRET,
                 "TEST" if cashfree_settings.TEST else "PROD", public_key=cashfree_settings.PAYOUT_PUBLIC_KEY)

init_payout()


@authorize
def request_async_transfer(beneId, transferId, amount, **kwargs):
    """Request Async Transfer.
    :param beneId: BeneId.
    :param transferId: transferId.
    :param amount: amount.
    :param transferMode: (optional) transferMode.
    :param remarks: (optional) remarks.
    :return: :class:`Response <Response>` object.
    :rtype: requests.Response.
    """
    req_transfer_req = RequestTransfer(beneId=beneId, transferId=transferId, amount=amount, **kwargs)
    req_transfer_req.end_point = "/payout/v1/requestAsyncTransfer"
    return __request.trigger_request(req_transfer_req)


def get_cashgram_link(reward):
    cash_id = F"{reward.reward_id}"
    expiry = (timezone.localdate() + timezone.timedelta(days=6)).strftime('%Y/%m/%d')
    response = Cashgram.create_cashgram(cashgramId=cash_id, amount=str(reward.amount), name=reward.user.get_full_name(),
                                        email=reward.user.email, phone=F"{reward.user.phone_number.national_number}",
                                        linkExpiry= expiry, remarks="", notifyCustomer=1)
    return CFResponse().set_response(response).data