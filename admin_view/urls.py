from django.urls import path

from admin_view.admin_views import transaction_dashboard, transaction_status, withdraw_request_list, \
    process_withdraw_request

urlpatterns = [
    path('transaction_dashboard/', transaction_dashboard, name='transaction_dashboard'),
    path('transaction_dashboard/status', transaction_status, name='transaction_status'),
    path('withdraw_request/', withdraw_request_list, name='withdraw_request'),
    path('withdraw_request/<str:action>/<uuid:pk>/', process_withdraw_request, name='process_withdraw_request')
]