from django.conf.urls import url
from django.urls import path

from api.payment.views import UserWithdrawRequestAPIView, PaymentSubscriptionAPIView, subscription_webhook_callback, \
    subscription_complete_callback, payout_withdraw_webhook_callback

urlpatterns = (
    path('subscription/<uuid:pk>/', PaymentSubscriptionAPIView.as_view()),
    path('subscription/detail/<int:reference_id>/', PaymentSubscriptionAPIView.as_view()),
    path('subscription/webhook_callback', subscription_webhook_callback),
    path('subscription-callback', subscription_complete_callback ),
    path('subscriptions/', PaymentSubscriptionAPIView.as_view()),
    url(r'^$',  UserWithdrawRequestAPIView.as_view()),
    path('withdraw/callback_webhook', payout_withdraw_webhook_callback)
)
