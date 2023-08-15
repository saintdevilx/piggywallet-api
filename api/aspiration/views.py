from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from api import PaginatedAPIView
from api.aspiration.models import Aspiration
from api.aspiration.serializers import AspirationDetailSerializer, AspirationListSerializer
from lib.utils import logger


class AspirationAPIView(APIView):
    """
    Aspiration res api view to list all aspiration and to get single aspiration detail
    """
    def get(self, request, pk=None):
        if pk:
            aspiration = get_object_or_404(Aspiration, pk=pk)
            data = AspirationDetailSerializer(aspiration).data
            return Response(data, status=status.HTTP_200_OK)
        else:
            return self.list(request)

    def list(self, request):
        aspirations = Aspiration.objects.all().order_by('featured')
        data = PaginatedAPIView().get_paginated_response_data(request, aspirations, AspirationListSerializer,
                                                              many=True).data
        return Response(data, status=status.HTTP_200_OK)