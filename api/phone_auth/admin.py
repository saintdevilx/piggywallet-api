from django.contrib import admin

from .models import PhoneToken
from ..user.models import User


class PhoneTokenAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp', 'timestamp', 'attempts', 'used')
    search_fields = ('phone_number', )
    list_filter = ('timestamp', 'attempts', 'used')
    readonly_fields = ('phone_number', 'otp', 'timestamp', 'attempts')


class UserAdmin(admin.ModelAdmin):
    list_display = ('pk', 'first_name', 'last_name', 'phone_number', 'date_joined')
    search_fields = ('phone_number', 'first_name', 'last_name', 'email')
    list_filter = ('kyc_completed', 'email_verified')
    readonly_fields = ('username', 'date_joined', 'last_login')


admin.site.register(PhoneToken, PhoneTokenAdmin)
admin.site.register(User, UserAdmin)