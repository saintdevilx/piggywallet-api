from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from api import PaginatedAPIView
from api.reward.apps import ANDROID_PLAYSTORE_APP_LINK, REFERER_MESSAGE
from api.reward.models import Reward, Offer
from api.reward.serializers import RewardSerializer, OfferDetailSerializer
from api.user.models import UserBankAccount
from lib.utils import logger


class RewardAPIView(PaginatedAPIView):
    def get(self, request):
        queryset = Reward.get_reward_for_user(request.user)
        response = self.get_paginated_response_data(request=request, queryset=queryset,
                                                    serializer_class=RewardSerializer, many=True)
        logger.debug(response)
        return response

    def post(self, request, pk, action):
        reward = get_object_or_404(Reward, pk=pk, user=request.user)
        if action.lower() == "opened":
            reward.set_opened()
        elif action.lower() == "redeem":
            bank_id = request.data['bank_id']
            bank_account = get_object_or_404(UserBankAccount, pk=bank_id, user=request.user)
            response = reward.redeem_reward(bank_account)
        response = RewardSerializer(reward).data
        return Response(response)


class OfferDetailAPIView(APIView):
    def get(self, request, slug=None, pk=None):
        logger.debug((request.GET, slug, pk, '------'))
        if slug:
            offer = get_object_or_404(Offer, slug=slug)
        elif pk:
            offer = get_object_or_404(Offer, pk=pk)
        else:
            offers = PaginatedAPIView().get_paginated_response_data(request, Offer.get_all_offers(),
                                                                  OfferDetailSerializer, many=True )
            return Response(offers.data)

        offer_data = OfferDetailSerializer(offer).data

        if slug == 'referral':
            offer_data['action'] = request.user.get_or_create_referral_code()
            offer_data['message'] = REFERER_MESSAGE
        return Response(offer_data)


class ReferralAPIView(APIView):
    def get(self, request, slug):
        # offer = get_object_or_404(Offer, Q(slug=slug)| Q(pk=slug))
        # offer_data = OfferDetailSerializer(offer).data
        # offer_data['action'] = ANDROID_PLAYSTORE_APP_LINK + request.user.get_or_create_referral_code()
        # offer_data['message'] = REFERER_MESSAGE
        # return Response(offer_data)
        pass
