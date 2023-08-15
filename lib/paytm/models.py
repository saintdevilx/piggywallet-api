class PaymentStatus:
    """
    Payment status response
    """
    TXNID = None
    BANKTXNID = None
    ORDERID = None
    TXNAMOUNT = None
    STATUS = None
    TXNTYPE = None
    GATEWAYNAME = None
    RESPCODE = None
    RESPMSG = None
    BANKNAME = None
    MID = None
    PAYMENTMODE = None
    REFUNDAMT = None
    TXNDATE = None
    RESULTSTATUS = None
    RESULTCODE = None
    RESULTMSG = None

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v.replace('TXN_','') if v and isinstance(v, str) else v)

    def get_status(self):
        return self.RESULTSTATUS or self.STATUS

    def get_amount(self):
        return self.TXNAMOUNT

    def get_response_code(self):
        return self.RESULTCODE or self.RESPCODE

    def get_response_msg(self):
        return self.RESULTMSG or self.RESPMSG

    def get_payment_mode(self):
        return self.PAYMENTMODE

    def get_transaction_date(self):
        return self.TXNDATE

    def get_order_id(self):
        return self.ORDERID

    def get_transaction_id(self):
        return self.TXNID

    def get_transaction_type(self):
        return self.TXNTYPE

    def get_refund_amount(self):
        return self.REFUNDAMT

    def get_bank_transaction_id(self):
        return self.BANKTXNID

    def get_gateway_name(self):
        return self.GATEWAYNAME

    def get_status_data(self):
        return {
            'status': self.get_status(),
            'ref_id': self.get_order_id(),
            'mode': self.get_payment_mode()
        }

class PaymentStatusExtended(PaymentStatus):
    def __init__(self, **kwargs):
        if kwargs.get('resultInfo'):
            result_info = kwargs.pop('resultInfo')
            kwargs.update(result_info.__dict__)
        for k,v in kwargs.items():
            setattr(self, k.upper(), v.replace('TXN_', '') if v else v)