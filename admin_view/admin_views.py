from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from api.payment.models import UserWithdrawRequest
from api.saving_goal.models import Transaction, SavingGoal
from lib.cashfree.webhook import PayoutWebhookResponse, PayoutWebhookEvent
from lib.utils import logger


@staff_member_required
def transaction_dashboard(request):
    logger.debug((request.POST))
    field_name = request.GET.get('field_name')
    field_value = request.GET.get('field_value')
    if field_name and field_value:
        kw = {field_name:field_value}
        logger.debug(kw)
        transactions = Transaction.objects.filter(**kw)[:100]
        logger.debug(transactions.count())
    return render(request, 'admin/transactions.html', locals())


@staff_member_required
@csrf_exempt
def transaction_status(request):
    response_data={}
    if request.method == 'POST':
        tid = request.POST['tid']
        transaction = get_object_or_404(Transaction, pk=tid)
        trans, response = transaction.get_or_set_status(transaction.pk, transaction.order_id)
        response_data = render_to_string('admin/transactions/status_response.html', locals())
    return JsonResponse({'success': True, 'html':response_data})


@staff_member_required
@csrf_exempt
def withdraw_request_list(request):
    order_by = request.GET.get('order', '-created_at')
    search_by = request.GET.get('q')
    status = request.GET.get('status', '0')
    page = request.GET.get('page', 1)
    MAX_RESULTS = 10
    _withdraw_requests_list = UserWithdrawRequest.get_withdraw_request(order_by=order_by, search_by=search_by,
                                                                       status=status)
    paginator = Paginator(_withdraw_requests_list, MAX_RESULTS)
    withdraw_requests = paginator.page(page)
    return render(request, 'admin/withdraw/withdraw_list.html', locals())


@staff_member_required
@csrf_exempt
def process_withdraw_request(request, action, pk):
    if request.method == 'POST':
        withdraw_request = get_object_or_404(UserWithdrawRequest, pk=pk)
        try:
            response = PayoutWebhookResponse({})
            response.transfer_id = pk
            if action == 'approve':
                response.event = PayoutWebhookEvent.TRANSFER_SUCCESS
                withdraw_request.process_withdraw_request(response)
            elif action == 'decline':
                response.event = PayoutWebhookEvent.TRANSFER_FAILED
                withdraw_request.process_withdraw_request(response)
            data = {'success':True}
        except Exception as ex:
            logger.exception("can not approve withdraw #processWithdrawFailed")
            data = {'error':True, 'msg':str(ex)}
        return JsonResponse(data)



class SavingGoalListAPIView(APIView):
    permission_classes = []

    def get(self, request, pk=None):
        savings = SavingGoal.all_objects.all()

    def post(self, request):
        pass