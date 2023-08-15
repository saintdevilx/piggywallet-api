#import sys


# def test_auto_collect_virtual_account_create():
#     from lib.cashfree.autocollect import AutoCollect
#     from lib.utils import logger
#     from api.user.models import User
#     import random
#     from .cashfree_settings import PRODUCTION, TEST
#     if not TEST or PRODUCTION:
#         return
#     ind = random.randrange(0,User.objects.count())
#     user = User.objects.all()[ind]
#     auto = AutoCollect()
#     # logger.debug(('token', auto.token))
#     res = auto.create_virtual_account(user)
#     logger.debug(res)
#     # assert res.subCode == "200"
#     return res


# def test_payout_withdraw():
#     from api.payment.models import UserWithdrawRequest
#     from lib.cashfree.cashfree_settings import PRODUCTION, TEST
#     if not TEST or PRODUCTION:
#         return
#     request = UserWithdrawRequest.objects.first()
#     # request.user_bank_account.add_beneficiery()
#     res = request.initiate_withdraw()
#     print(res)


# def test_upi_submit():
#     from api.saving_goal.models import Transaction
#     from lib.cashfree.payment_gateway import UPIGateway
#     from api.saving_goal.serializers import TransactionSerializer
#     from pprint import pprint
#     from mpw import settings
#     from lib.cashfree import cashfree_settings
#     if not settings.DEBUG or cashfree_settings.PRODUCTION or not cashfree_settings.TEST:
#         return
#     tr = Transaction.objects.all()[4]#first()
#     data = TransactionSerializer(tr).data
#     data.update({'full_name': tr.user.get_full_name(), 'email': tr.user.get_email(),
#                  'phone': str(tr.user.phone_number.national_number), 'upi_vpa':'testsuccess@gocash'})
#     pprint(data)
#     res = UPIGateway().submit(data)
#     print(res)

# test_upi_submit()

def test_upi_order_status():
    from api.saving_goal.models import Transaction
    from lib.cashfree.payment_gateway import UPIGateway
    tr = Transaction.objects.first()
    res = UPIGateway().get_order_status(tr.order_id)
    print(res.__dict__)

test_upi_order_status()

# def run():
# test_auto_collect_virtual_account_create()
#run()

#test_payout_withdraw()
