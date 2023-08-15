from django.conf.urls import url
from django.urls import path

from api.reward.views import RewardAPIView, ReferralAPIView, OfferDetailAPIView

urlpatterns = [
    url('^$', RewardAPIView.as_view()),
    path('<uuid:pk>/<str:action>', RewardAPIView.as_view()),
    path('offers', OfferDetailAPIView.as_view()),
    path('offer_details/<str:slug>', OfferDetailAPIView.as_view()),
    path('offer_details/<uuid:pk>', OfferDetailAPIView.as_view()),
]