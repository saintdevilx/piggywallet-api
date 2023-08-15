from django.contrib import admin

# Register your models here.
from django.contrib.admin import  ModelAdmin
from django.urls import reverse
from django.utils.safestring import mark_safe

from api.payment.models import UserWithdrawRequest


class AdminUserWithdrawRequest(ModelAdmin):
    list_display = ['pk', 'withdraw_amount', 'status', 'user_profile', 'created_at']
    readonly_fields = ['withdraw_amount', 'saving_goal', 'user', 'deleted_at']
    search_fields = []
    raw_id_fields = ['user_bank_account', 'transaction']
    list_filter = ['status']

    def user_profile(self, obj):
        user_link = reverse('admin:user_user_change', args=(obj.user_id,))
        return mark_safe(F'<a href="{user_link}">{obj.user.get_full_name()}</a>')


admin.site.register(UserWithdrawRequest,AdminUserWithdrawRequest)