from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination configuration for product catalog.
    Returns 12 items per page by default (good for grid layouts).
    """

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100


    def get_paginated_response(self, data):

        return super().get_paginated_response(data)
