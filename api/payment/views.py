import json

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from api import PaginatedAPIView
from api.payment.exceptions import InvalidSubscriptionDetails
from api.payment.models import PaymentSubscription
from api.payment.serializers import UserWithdrawRequestWriteSerializer, PaymentSubscriptionSerializer, \
    PaymentSubscriptionListSerializer
from api.reward.models import Reward
from api.saving_goal.exceptions import InsufficientBalance, ActiveWithdrawRequest
from api.saving_goal.models import SavingGoal, Transaction
from lib.cashfree.webhook import PayoutWebhookResponse
from lib.utils import logger, ErrorResponse
from cashfree_sdk import verification
from django.http import JsonResponse

from mpw import settings


class UserWithdrawRequestAPIView(APIView):
    """
    withdraw request REST api
    """
    def post(self, request):
        withdraw_request = UserWithdrawRequestWriteSerializer(data=request.data)
        # logger.debug((request.data))
        if withdraw_request.is_valid():
            try:
                logger.debug(withdraw_request.validated_data)
                #saving_goal = get_object_or_404(SavingGoal, pk=withdraw_request.validated_data['saving_goal'])
                withdraw_request.create_withdraw_request(request.user)
            except InsufficientBalance:
                response_data = {
                    'message': "Insufficient balance",
                    'error': True
                }
                return ErrorResponse(response_data['message'])
            except ActiveWithdrawRequest:
                response_data = {
                    "message": "A withdraw request already exist",
                    "error": True
                }
                return ErrorResponse(response_data['message'])
            except Exception as ex:
                logger.exception("Withdraw request exception")
                return Response({"error": "something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(withdraw_request.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentSubscriptionAPIView(APIView):
    """
    Payment subscription REST APIs.
    """
    def get(self, request, pk=None):
        if not pk:
            return self.list(request)
        try:
            subscription = get_object_or_404(PaymentSubscription, saving_goal_id=pk, saving_goal__user=request.user)
        except Http404 as not_found:
            try:
                saving_goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
                subscription = PaymentSubscription.create_subscription(saving_goal, saving_goal.user)
            except InvalidSubscriptionDetails as ex:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        data = PaymentSubscriptionSerializer(subscription).data
        if settings.DEBUG:
            data['enabled'] = False
            data['message'] = 'Sorry Auto debit option is not working. our team is working on it.'
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, pk=None):
        subscription = get_object_or_404(PaymentSubscription, pk=pk, saving_goal__user=request.user)
        response = subscription.cancel_subscription(request.user)
        logger.debug(response)
        if not response:
            logger.debug(response)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_200_OK)

    def list(self, request, pk=None):
        subscription_list = PaginatedAPIView().get_paginated_response_data(
            request, PaymentSubscription.get_user_subscriptions(request.user),
            PaymentSubscriptionListSerializer, many=True
        )
        return Response(subscription_list.data, status=status.HTTP_200_OK)


class PaymentSubscriptionDetails(APIView):
    def post(self, request, reference_id):
        payment_subscription = get_object_or_404(PaymentSubscription, reference_id=reference_id,
                                                 saving_goal_user=request.user)
        subscription = payment_subscription.get_subscription_details(reference_id, request.user)
        return Response(subscription, status=status.HTTP_200_OK)


@csrf_exempt
def subscription_webhook_callback(request):
    if request.method == "POST":
        event_type = request.POST['cf_event']
        if event_type == "SUBSCRIPTION_STATUS_CHANGE":
            pass
        elif event_type == "SUBSCRIPTION_PAYMENT_DECLINED":
            pass
        elif event_type == "SUBSCRIPTION_NEW_PAYMENT":
            reference_id = request.POST['cf_subReferenceId']
            amount = request.POST['cf_amount']
            subscription = get_object_or_404(PaymentSubscription, reference_id=reference_id)
            saving = subscription.saving
            transaction = Transaction.create(saving.user, saving, Transaction.TRANSACTION_TYPE_CREDIT, amount)
            transaction.update_status(transaction.order_id, "SUCCESS")
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@csrf_exempt
@xframe_options_exempt
def subscription_complete_callback(request):
    if request.method == "POST":
        logger.debug(request.POST)
        callback_data = request.POST
        reference_id = request.POST['cf_subReferenceId']
        sub_id = request.POST['cf_subscriptionId']
        subscription = get_object_or_404(PaymentSubscription, reference_id=reference_id, subscription_id=sub_id)
        subscription.update_status(callback_data)
        return render(request, 'subscription_auth_callback.html', {'callback_data': callback_data})
    return render(request, 'subscription_auth_callback.html', {'callback_data': {}})


@csrf_exempt
def payout_withdraw_webhook_callback(request):
    logger.debug(('request', request.POST, '=====>>>>><<<<======='))
    if request.method == "POST":
        response = PayoutWebhookResponse(request.POST)
        webhook_data = response.json()
        logger.debug((webhook_data, type(webhook_data)))
        is_valid = verification.verify_webhook(webhook_data, 'JSON')
        if is_valid:
            from api.payment.models import UserWithdrawRequest
            if str(response.transfer_id).startswith('reward_'):
                Reward.process_reward(response)
            else:
                UserWithdrawRequest.process_withdraw_request(response)
            status = True
        else:
            logger.debug(('invalid....', request.POST.dict()))
            status = False
        return JsonResponse({})