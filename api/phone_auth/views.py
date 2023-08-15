import logging

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.user.serializers import UserDetailReadSerializer
from lib.global_config import get_global_config
from .models import PhoneToken
from .serializers import (
    PhoneTokenCreateSerializer, PhoneTokenValidateSerializer,
)
from .utils import user_detail

logger = logging.getLogger('application')


class GenerateOTP(CreateAPIView):
    authentication_classes = []
    permission_classes = []

    queryset = PhoneToken.objects.all()
    serializer_class = PhoneTokenCreateSerializer

    def post(self, request, format=None):
        # Get the patient if present or result None.
        logger.debug(request.data)
        ser = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        if ser.is_valid():
            token = PhoneToken.create_otp_for_number(
                request.data.get('phone_number')
            )
            if token:
                phone_token = self.serializer_class(
                    token, context={'request': request}
                )
                data = phone_token.data
                if getattr(settings, 'PHONE_LOGIN_DEBUG', False):
                    data['debug'] = token.otp
                    logger.debug(F"OTP: {token.otp}")
                return Response(data)
            return Response({
                'reason': "you can not have more than {n} attempts per day, please try again tomorrow".format(
                    n=getattr(settings, 'PHONE_LOGIN_ATTEMPTS', 10))}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)


class ValidateUserAPIView(CreateAPIView):
    authentication_classes = []
    permission_classes = []

    queryset = PhoneToken.objects.all()
    serializer_class = PhoneTokenValidateSerializer

    def post(self, request, format=None):
        # Get the patient if present or result None.
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            pk = request.data.get("otp_ref")
            otp = request.data.get("otp")

            try:
                extra_fields = {
                    "referrer":request.data.get('referrer'),
                    "device_id":request.data.get('device_id')
                }
                user = authenticate(request, pk=pk, otp=otp, **extra_fields)
                login(request, user)
                response = user_detail(user)
                return Response(response, status=status.HTTP_200_OK)
            except ObjectDoesNotExist:
                return Response(
                    {'reason': "OTP doesn't exist"},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)


class UserDetail(APIView):

    def get(self, request):
        user_data = UserDetailReadSerializer(request.user).data
        response = {
            'user': user_data,
            'config': get_global_config()
        }
        return Response(response)


class ResendOTPSmsAPIView(APIView):

    def post(self, request):
        PhoneToken.create_otp_for_number(request.data['number'])