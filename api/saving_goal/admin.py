from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from api.saving_goal.models import SavingGoal, Transaction


class SavingGoalAdmin(admin.ModelAdmin):
    list_display = ['pk', 'title', 'target_amount', 'current_amount', 'target_date', 'status', 'deposit_frequency',
                    'deduction_mode', 'deduction_amount']
    search_fields = ['title', 'user__first_name', 'user__last_name', 'user__email', 'user__phone_number']
    readonly_fields = []
    list_filter = ['status', 'deposit_frequency', 'deduction_mode']

admin.site.register(SavingGoal, SavingGoalAdmin)


class AdminTransaction(admin.ModelAdmin):
    list_display = ['pk', 'order_id', 'amount', 'amount_before', 'amount_after', 'created_at', 'status', 'type',
                    'user_profile', 'check_status']
    list_filter = ['status']
    readonly_fields = []
    search_fields = ['user__email', 'user__phone_number']

    def user_profile(self, obj):
        user_link = reverse('admin:user_user_change', args=(obj.user_id,))
        return mark_safe(F'<a target="_blank" href="{user_link}">{obj.user.get_full_name()}</a>')

    def check_status(self, obj):
        link = reverse('admin_view:transaction_dashboard')
        return mark_safe(F"<a target='_blank' href='{link}?field_name=pk&field_value={obj.pk}'>check Status</a>")


admin.site.register(Transaction, AdminTransaction)