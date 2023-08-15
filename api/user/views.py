from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from api.user.exceptions import EmailAlreadyExists, VerificationLinkExpired, InvalidJWTToken
from api.user.models import UploadFile, UserContact, UserSMS, UserKYCDetail, User
from api.user.serializers import UserDetailWriteSerializer, UserDetailReadSerializer, UserKYCDetailSerializer
from api.user.tasks import update_user_contact, update_user_sms_data
from lib.kyc_verification import get_user_kyc_data
from lib.utils import logger, validate_and_decode_firebase_id_token, ErrorResponse, getContentFileFromBase64, \
    get_jwt_token


class UserProfileDetail(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = {}
        logger.debug(request.data)
        if request.data.get('provider') == 'google':
            user = validate_and_decode_firebase_id_token(request.data['idToken'])
            logger.debug(user)
            if user:
                try:
                    request.user.update_details_via_google(user)
                    data = UserDetailReadSerializer(request.user).data
                except EmailAlreadyExists as ex:
                    return ErrorResponse("Email already associated with another user's account")
                return Response(data)
            else:
                return ErrorResponse("Invalid user details")
        else:
            data = UserDetailWriteSerializer(request.user, data=request.data)
            if data.is_valid():
                user_data = request.data.copy()
                if user_data.get('email') and request.user.email and request.user.email_verified:
                    user_data.pop('email')
                user_data['name'] = data.validated_data['full_name']
                try:
                    request.user.update_details(user_data)
                    data = UserDetailReadSerializer(request.user).data
                except EmailAlreadyExists as ex:
                    return ErrorResponse("Email already associated with another account")
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response(data.errors, status=status.HTTP_403_FORBIDDEN)

    def get(self, request):
        user = get_object_or_404(User, pk=request.user.pk)
        data = UserDetailReadSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class UserProfileImage(APIView):
    def post(self, request):
        url_data = UploadFile.create('profile',request.user)
        if url_data:
            return Response(url_data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        logger.debug(request.user)
        image = get_object_or_404(UploadFile, pk=pk, user=request.user)
        if image:
            request.user.set_image(image)
            return Response(status=status.HTTP_200_OK)


class UserContactAPIView(APIView):
    """
    User contact list API

    expect request data format a list of contact with name and number
    e.g. [{'name': '', 'number': ''},
          {'name': '', 'number': ''},
          {'name': '', 'number': ''},
          ....]
    """

    def post(self, request):
        logger.debug(request.data[0])
        update_user_contact.delay(request.user.pk, request.data)
        #UserContact.create(request.data, request.user)
        return Response(status=status.HTTP_200_OK)


class SMSDataAPIView(APIView):
    """
    store user sms
    e.g. [{"sender":"....", "text":"...", "received_on":"..."}
    ]
    """
    def post(self, request):
        logger.debug(request.data[:5])
        update_user_sms_data.delay(request.user.pk, request.data)
        return Response(status=status.HTTP_200_OK)


class KYCAPIView(APIView):
    """
    """
    #parser_class = (FormParser,)
    def post(self, request):
        logger.debug(request.data)
        _type = request.data.get('type')
        try:
            if _type == 'offline':
                serializer = UserKYCDetailSerializer(data=request.data)
                if serializer.is_valid():
                    data, _status = serializer.get_or_create(request.user)
                return Response(status=_status.HTTP_200_OK)
            else:
                file = request.data.get('file') or getContentFileFromBase64(request.data.get('offline_kyc_file'))
                kyc_data, xml_data = get_user_kyc_data(file, request.data['share_code'], phone_no=request.data['phone'],
                                             email=request.data.get('email',''))
                logger.debug(kyc_data['validation'])
                data = {}
                data.update(kyc_data['personal_data'])
                data.update(kyc_data['validation'])
                # get or create kyc detail
                kyc_data, _status = request.user.get_or_create_kyc(data, request.data['share_code'], str(xml_data))
                logger.debug(kyc_data)
                data = UserKYCDetailSerializer(kyc_data).data
                return Response(data, status=status.HTTP_200_OK)
        except Exception as ex:
            logger.exception(ex)
            return ErrorResponse('Check if file and Security code are correct',status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            kyc_data = get_object_or_404(UserKYCDetail, user=request.user)
            data = UserKYCDetailSerializer(kyc_data).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Response(status=status.HTTP_404_NOT_FOUND)


def email_verification(request, jwt_token, template='email_verification.html'):
    try:
        User.verify_email_verification_token(jwt_token)
        return render(request, template, {'verified':True} )
    except InvalidJWTToken as ex:
        return render(request, template, {'invalid': True})
    except VerificationLinkExpired as ex:
        return render(request, template, {'expired': True})
    except Exception as ex:
        return render(request, template, {'expired':True})


class UserEmailVerification(APIView):
    def post(self, request):
        request.user.send_verification_email()
        return Response({'success':True})

@staff_member_required
def get_email_verification(request):
    logger.debug('verification token....')
    response = {
        'verification_token': str(request.user.get_email_verification_token().decode('utf-8'))
    }
    return JsonResponse(response)