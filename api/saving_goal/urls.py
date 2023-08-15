from django.urls import path

from api.saving_goal.views import SavingGoalView, SavingGoalTransactionView, transaction_webhook, TransactionListView, \
    transaction_payment_redirect, TransactionStatusView

urlpatterns =[
    path('<uuid:pk>/', SavingGoalView.as_view(), name='saving_goal_api'),
    path('<uuid:pk>/<str:action>/', SavingGoalTransactionView.as_view(), name='saving_goal_transaction_api'),
    path('transactions/', TransactionListView.as_view(), name='transaction_list_api'),
    path('<str:action>/', SavingGoalTransactionView.as_view(), name='saving_goal_transaction_api'),
    path('transaction/<uuid:pk>/', TransactionStatusView.as_view(), name='saving_transaction_api'),
    path('transaction/callback_webhook', transaction_webhook, name="transaction_webhook_callback"),
    path('transaction/payment_redirect', transaction_payment_redirect, name='payment_redirect'),
    path('', SavingGoalView.as_view(), name='saving_goal_api'),
]