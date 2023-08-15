from django.contrib import admin

from api.reward.models import Reward, Offer

class RewardAdmin(admin.ModelAdmin):
	raw_id_fields=['user']

admin.site.register(Reward, RewardAdmin)
admin.site.register(Offer)
