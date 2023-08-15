from rest_framework import serializers
from api.aspiration.models import Aspiration
from lib.utils import logger
from mpw import settings


class AspirationListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Aspiration
        fields = ['title', 'image', 'pk', 'description', 'short_description', 'icon_image']

    def get_image(self, obj):
        return obj.image.url if obj.image else ""


class AspirationDetailSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Aspiration
        fields = ['pk', 'title', 'description', 'image', 'target_date', 'target_days', 'target_amount', 'completed',
                  'in_progress', 'appreciation', 'follower']

    def get_image(self, obj):
        return str(obj.image.url) if obj.image else ""
