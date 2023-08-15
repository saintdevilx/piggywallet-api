from collections import OrderedDict

from django.core.paginator import EmptyPage
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from lib.utils import logger


class PaginatedAPIView(APIView):
    page_size_query_param = 'page_size'
    max_page_size = 20

    def get_paginated_serialized_response(self, paginator, data):
        return Response(OrderedDict([
            #('count', paginator.page.count),
            ('next_page_number', paginator.page.next_page_number() if data and paginator.page.has_next() else None),
            ('has_next', paginator.page.has_next() if data else False),
            ('results', data)
        ]))

    def get_paginated_response_data(self, request, queryset, serializer_class, many=False):
        paginator = PageNumberPagination()
        try:
            page_data = paginator.paginate_queryset(queryset, request)
        except Exception as ex:
            page_data = ()

        serialized_data = serializer_class(page_data, many=many).data if page_data else []
        response = self.get_paginated_serialized_response(paginator, serialized_data)

        return response
