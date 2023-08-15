from django.conf.urls import url
from django.urls import path

from api.saving_goal.views import UserBankAccountCreateUpdate
from api.user.views import UserProfileDetail, UserProfileImage, UserContactAPIView, SMSDataAPIView, KYCAPIView, \
    email_verification, get_email_verification, UserEmailVerification

urlpatterns =[
    url(r'detail/$', UserProfileDetail.as_view(), name='profile_detail'),
    url(r'bank-account/$', UserBankAccountCreateUpdate.as_view(), name="user_bank_detail"),
    path('bank-account/<uuid:pk>/', UserBankAccountCreateUpdate.as_view(), name="user_bank_detail"),
    path('change-image/<uuid:pk>/', UserProfileImage.as_view(), name='change_profile_image'),
    path('change-image', UserProfileImage.as_view(), name='change_profile_image'),
    path('contact-list/', UserContactAPIView.as_view(), name='user_contact_list'),
    path('sms-data/', SMSDataAPIView.as_view(), name='sms_data'),
    path('user-kyc/', KYCAPIView.as_view() , name='user_offline_kyc'),
    path('send-email-verification/', UserEmailVerification.as_view() , name='send_email_verification'),
    path('email-verification/<str:jwt_token>', email_verification, name="email_verification_link"),
    path('email-verification-token/', get_email_verification, name='email_verification_token')
]
