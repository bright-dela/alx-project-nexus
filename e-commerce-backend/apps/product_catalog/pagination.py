from rest_framework.pagination import PageNumberPagination


class StandardProductsPagination(PageNumberPagination):
    """
    Standard pagination configuration for product catalog.
    Returns 12 products per page (good for grid layout).
    """

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return super().get_paginated_response(data)