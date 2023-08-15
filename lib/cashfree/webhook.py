import json


class WebhookResponse:
    def __init__(self, data):
        for var in dir(self):
            if not var.startswith('_'):
                f = var.split('_')
                key = f[0] + "".join([i[0].upper()+i[1:] for i in f[1:]]) if len(f) > 1 else f[0]
                if data.get(key):
                    setattr(self, var, data.get(key))

    def data(self):
        return {var: getattr(self, var) for var in dir(self) if not var.startswith('_')
                and getattr(self, var) and not getattr(getattr(self, var), '__call__', None)
                }

    def json(self):
        try:
            return json.dumps(self.data())
        except:
            return {}


class PayoutWebhookEvent:
    TRANSFER_SUCCESS = 'TRANSFER_SUCCESS'  # Transfer successful at the bank and account debited
    TRANSFER_FAILED = 'TRANSFER_FAILED'  # Transfer failed
    TRANSFER_REVERSED = 'TRANSFER_REVERSED'  # Transfer reversed by the beneficiary bank
    CREDIT_CONFIRMATION = 'CREDIT_CONFIRMATION'  # Confirmation of balance credit
    TRANSFER_ACKNOWLEDGED = 'TRANSFER_ACKNOWLEDGED'  # After the beneficiary bank has deposited the money it confirms the transfer.
    LOW_BALANCE_ALERT = 'LOW_BALANCE_ALERT'  # Payouts recharge account low balance alert


class PayoutWebhookResponse(WebhookResponse):
    event = None
    signature = None
    utr = None
    transfer_id = None
    bene_id = None
    acknowledged = None
    reference_id = None
    name = None
    bank_account = None
    ifsc = None
    event_time = None
    reason = None
    ledger_balance = None
    amount = None
    current_balance = None
    alert_time = None
    cashgram_id =None


class AutoCollectWebhookEvent:
    AMOUNT_COLLECTED = "AMOUNT_COLLECTED"
    AMOUNT_REJECTED = "AMOUNT_REJECTED"
    AMOUNT_SETTLED = "AMOUNT_SETTLED"


class AutoCollectWebhookResponse(WebhookResponse):
    event = None
    amount = None
    v_account_id = None
    virtual_vpa_id = None
    v_account_number = None
    is_vpa = None
    email = None
    phone = None
    reference_id = None,
    utr = None
    credit_ref_no = None
    remitter_account = None
    remitter_name = None
    payment_time = None
    signature = None

    # reject event
    reject_id = None
    reason = None

    # amount settled event
    settlement_id = None
    count = None

#    def __init__(self, **kwargs):
