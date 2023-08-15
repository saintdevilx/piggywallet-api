import json
from datetime import datetime
from time import strptime

from cashfree_sdk.verification import verify_webhook
from django.http import Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.csrf import csrf_exempt
from paytmpg import MerchantProperty
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api import PaginatedAPIView
from api.payment.models import PaymentSubscription
from api.payment.serializers import PaymentSubscriptionSerializer
from api.saving_goal import utils
from api.saving_goal.exceptions import InsufficientBalance, ActiveWithdrawRequest
from api.saving_goal.models import SavingGoal, Transaction
from api.saving_goal.serializers import SavingGoalWriteSerializer, SavingGoalReadSerializer, \
    SavingGoalTransactionSerializer, TransactionSerializer
from api.saving_goal.utils import verify_response_signature
from api.user.models import UserBankAccount, User
from api.user.serializers import UserBankAccountSerializer
from lib.cashfree.autocollect import AutoCollect
from lib.cashfree.payment_gateway import UPIGateway, UPICallbackResponse
from lib.cashfree.webhook import AutoCollectWebhookEvent, AutoCollectWebhookResponse
from lib.paytm.models import PaymentStatus
from lib.paytm.paytm_utils import initiate_transaction, get_checksum, verify_response_checksum, get_status_checksum, \
    get_payment_status
from lib.utils import logger, ErrorResponse
from mpw import settings


class SavingGoalView(APIView):
    """
    Saving goal API view to create update and list and delete saving goal

    Create Saving Goal:
        Post: to create new saving goals with all the required data will be received at post
    Update Saving Goal:
        Post: to update and existing saving goal post the data with `pk` of saving goal along with data to be update
    Delete Saving Goal:
        Delete: to delete an existing saving goal request delete, and saving goal should be created by the logged in
        user in order to delete
    List saving goals:
        GET: if primary is provided only single object with provided pk will be returned
        list: if no primary key is provided all the saving goals created by logged in user will be returned with
        pagination
    """
    def post(self, request, pk=None):
        data = request.data.copy()
        data['user'] = request.user.pk
        target_date = parse_datetime(data['target_date']) or parse_date(data['target_date'])
        data['target_date'] = datetime.combine(target_date, datetime.min.time())
        goal = SavingGoalWriteSerializer(data=data)
        if goal.is_valid():
            if not pk:
                goal.create_update_saving_goal()
                data = SavingGoalReadSerializer(goal.instance).data

                # if goal.instance.deduction_mode == SavingGoal.AUTO_DEBIT:
                #     # for deduction mode as auto debit create subscription to auto deduct money periodically
                #     # create subscription and set the subscription status
                #     subscription = PaymentSubscription.create_subscription(goal.instance, request.user)
                #     data.update(PaymentSubscriptionSerializer(subscription).data)

                return Response(data, status=status.HTTP_201_CREATED)
            else:
                goal_instance = get_object_or_404(SavingGoal, pk=pk)
                goal = goal.create_update_saving_goal(instance=goal_instance)
                return Response(SavingGoalReadSerializer(goal).data, status=status.HTTP_200_OK)
        else:
            return Response(goal.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk=None, **kwargs):
        if not pk:
            data = self.list(request, **kwargs)
        else:
            goal_obj = get_object_or_404(SavingGoal, pk=pk, user=request.user)
            data = SavingGoalReadSerializer(goal_obj).data
        return Response(data, status=status.HTTP_200_OK)

    def list(self, request, **kwargs):
        """
        status query from http request to filter the list of saving goals, status is to determine the whether the
        saving goal is in progress , finished , cancelled etc.
        :param request:
        :param kwargs:
        :return:
        """
        status = request.GET.get('status', SavingGoal.SAVING_GOAL_IN_PROGRESS)
        goals = SavingGoal.get_saving_goals(user=request.user, status=status)
        data = PaginatedAPIView().get_paginated_response_data(request, goals, SavingGoalReadSerializer, many=True).data
        return data

    def delete(self, request, pk, **kwargs):
        saving = get_object_or_404(SavingGoal, pk=pk, user=request.user)
        saving.close_saving()
        return Response({}, status=status.HTTP_204_NO_CONTENT)


class SavingGoalTransactionView(APIView):
    """
    API view to handle different types of transaction made with saving goals
    """
    ALLOWED_ACTION = ['deposit', 'withdraw', 'transactions']

    def get(self, request, pk, action):
        if action != 'transactions':
            raise Http404
        saving_obj = get_object_or_404(SavingGoal, pk=pk)
        transactions = SavingGoal.get_transactions(saving_obj)
        data = PaginatedAPIView().get_paginated_response_data(request, transactions, TransactionSerializer, many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, pk, action):
        if action not in self.ALLOWED_ACTION:
            if settings.DEBUG:
                return Response("action is not valid is should be in `deposit`, `transactions` or `withdraw` "
                                "e.g. /<saving_goal_pk>/<action:(deposit , transactions or withdraw)>/")
            raise Http404

        if action == 'deposit':
            return self.deposit(pk, request)
        elif action == 'withdraw':
            return self.withdraw(pk, request)

    def deposit(self, pk, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        data = request.data.copy()
        data['saving_goal_pk'] = str(pk)
        data['type'] = Transaction.TRANSACTION_TYPE_CREDIT   # CREDIT to saving  wallet
        data = SavingGoalTransactionSerializer(data=data)
        return Response({"message":"updating policy not taking deposit anymore"}, status=status.HTTP_400_BAD_REQUEST)
        if data.is_valid():
            try:
                transaction_data = data.create_transaction(request.user)
                payload = {}
                payload.update(transaction_data)
                upi_vpa = request.data.get('upi_vpa') #if not settings.DEBUG else 'success@upi'
                payload.update({'full_name': request.user.get_full_name(), 'email': request.user.get_email(),
                                'phone': str(request.user.get_phone_number()), 'upi_vpa': upi_vpa})
                upi_res = dict(UPIGateway().submit(payload).get_data()) or {}
                upi_link = upi_res.get('link') #if not settings.DEBUG \
                #    else 'upi://pay?pa=deepakaimca@oksbi&pn=testing&tr=7116221&am=1&cu=INR&tn=testing%20%payment'
                logger.debug((upi_res, transaction_data))
                #transaction_data.update(upi_res)
                return Response({"UPI": upi_link, 'transaction_data': transaction_data})
            except Exception as ex:
                logger.exception(ex)
                return ErrorResponse("Something went wrong. please try after sometime",
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)

    def withdraw(self, pk, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        data = request.data.copy()
        data['saving_goal_pk'] = str(pk)
        data['type'] = Transaction.TRANSACTION_TYPE_CREDIT  # DEBIT from Saving wallet
        data = SavingGoalTransactionSerializer(data=data)
        if data.is_valid():
            try:
                response_data = data.create_transaction(request.user)
            except InsufficientBalance:
                response_data = {
                    'message': "Insufficient balance",
                    'error': True
                }
            except ActiveWithdrawRequest:
                response_data = {
                    "message": "A withdraw request already exist",
                    "error": True
                }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def transaction_webhook(request):
    """

    :param request:
    :return:
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.copy().dict()

        callback_data = UPICallbackResponse().set_response(data)
        is_valid = callback_data.verify()

        logger.debug(dict(callback_data.get_data()))

        if is_valid:
            oid = callback_data.orderId
            _status = str(callback_data.txStatus)
            amount = str(callback_data.orderAmount)
            Transaction.update_status(oid, _status, amount=amount, data=data)
            return JsonResponse({"success": True})
    raise Http404


class TransactionListView(PaginatedAPIView):
    def get(self, request):
        order_by = request.query_params.get('order_by', 'latest')
        type = request.query_params.get('type')
        timeline = request.query_params.get('timeline')
        logger.debug(F"{locals()}")
        try:
            transactions_list = Transaction.get_all_transaction(request.user, order_by=order_by, type=type,
                                                                timeline=timeline)
        except Exception as ex:
            logger.exception(ex)
            return ErrorResponse("Bad request")

        return self.get_paginated_response_data(request, transactions_list, TransactionSerializer, many=True)


class TransactionStatusView(APIView):
    """
    get transaction status
    """
    def get(self, request, pk):
        logger.debug(request)
        transaction = get_object_or_404(Transaction, pk=pk)
        if transaction.get_status() == Transaction.TRANSACTION_STATUS_INITIATED:
            status_data, _ = transaction.get_or_set_status(transaction.order_id)
            if not status_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            status_data = transaction
        response = TransactionSerializer(status_data).data
        return Response(response, status=status.HTTP_200_OK)


class UserBankAccountCreateUpdate(APIView):
    """
    """

    def get(self, request, pk=None):
        """
        list bank accounts associated with user
        :param request:
        :param pk:
        :return:
        """
        if not pk:
            accounts = UserBankAccount.get_user_account(request.user)
            data = UserBankAccountSerializer(accounts, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        else:
            bank_account = get_object_or_404(UserBankAccount, pk=pk)
            return Response(UserBankAccountSerializer(bank_account).data, status=status.HTTP_200_OK)

    def post(self, request, pk=None):
        bank_detail = UserBankAccountSerializer(data=request.data)
        if bank_detail.is_valid():
            bank_account, _ = UserBankAccount.create_or_update(request.user, request.data)
            data = UserBankAccountSerializer(bank_account).data
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(bank_detail.errors, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        bank_account = get_object_or_404(UserBankAccount, pk=pk)
        if bank_account.remove_bank_account(request):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_200_OK)


@csrf_exempt
def transaction_payment_redirect(request):
    """

    """
    logger.debug(request.POST)
    return HttpResponseRedirect(utils.get_payment_redirect_frontend_url(request))