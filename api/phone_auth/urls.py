from django.conf.urls import url

from .views import GenerateOTP, ValidateUserAPIView, UserDetail, ResendOTPSmsAPIView

urlpatterns = [
    url(r'^generate/$', GenerateOTP.as_view(), name="generate"),
    url(r'^validate/$', ValidateUserAPIView.as_view(), name="validate"),
    url(r'^user/detail$', UserDetail.as_view(), name="user_detail"),
]
