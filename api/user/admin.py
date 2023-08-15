from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.models import UserSMS, UserContact, UserKYCDetail, VirtualAccount, ReferredUser, UserBankAccount


class AdminUserKYCDetail(ModelAdmin):
    list_display = ['pk', 'name', 'gender', 'adhaar_no', 'address', 'dob', 'phone', 'email']
    search_fields = ['name', 'gender']
    readonly_fields = []
    raw_id_fields = []


admin.site.register(UserSMS)
admin.site.register(UserContact)
admin.site.register(UserKYCDetail, AdminUserKYCDetail)
admin.site.register(VirtualAccount)
admin.site.register(ReferredUser)
admin.site.register(UserBankAccount)