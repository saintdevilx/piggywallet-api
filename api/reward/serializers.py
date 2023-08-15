from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from api.reward.models import Reward, Offer


class RewardSerializer(ModelSerializer):

    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    expire_on = serializers.SerializerMethodField()

    class Meta:
        model = Reward
        fields = ['pk', 'created_at', 'type', 'amount', 'earned_for', 'status', 'cashgram_url', 'reference_id',
                  'expire_on']

    def get_type(self, obj):
        return obj.get_type_display()

    def get_status(self, obj):
        return obj.get_status_display()

    def get_expire_on(self, obj):
        print(type(obj.expire_on), '===', obj.expire_on)
        return obj.expire_on


class OfferDetailSerializer(ModelSerializer):
    class Meta:
        model = Offer
        fields = ["pk", "title", "short_description", "full_description", "expired_on", 'image', 'action_title',
                  'action_url']