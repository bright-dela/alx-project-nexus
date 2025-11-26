from rest_framework import viewsets, status, permissions, filters, mixins
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from django_filters.rest_framework import DjangoFilterBackend

from django.conf import settings

from .models import Category, Brand, Product, ProductReview

from .serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductReviewCreateSerializer,
    ProductReviewSerializer,
)

from .filters import ProductFilter
from .permissions import IsStaffOrReadOnly
from .pagination import StandardProductsPagination
from .cache import product_cache, product_list_key, product_detail_key, category_tree_key, brand_list_key

import logging
logger = logging.getLogger(__name__)

# Create your views here.


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Get only root nodes (categories with no parent)
        return Category.objects.filter(parent__isnull=True, is_active=True)
    
    def list(self, request, *args, **kwargs):
        key = category_tree_key()
        cached = product_cache.get(key)

        if cached:
            logger.info("Category tree retrieved from cache successfully with key: {key}")
            return Response(cached, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(self.get_queryset(), many=True)
        data = serializer.data
        product_cache.set(key=key, value=data, timeout=settings.CATEGORY_TREE_CACHE_TIMEOUT)

        logger.info("Category tree cached successfully with key: {key}")

        return Response(data, status=status.HTTP_200_OK)




class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset= Brand.objects.filter(is_active=True).order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        key = brand_list_key()
        cached = product_cache.get(key)

        if cached:
            logger.info("Brand list retrieved from cache successfully with key: {key}")

            return Response(cached, status=status.HTTP_200_OK)

        serializer = self.get_serializer(self.get_queryset(), many=True)
        data = serializer.data
        product_cache.set(key, data, timeout=60 * 60)
        logger.info(f"Brand list cached successfully with key: {key}")
        return Response(data, status=status.HTTP_200_OK)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("brand", "category").prefetch_related("images")

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-created_at"]

    pagination_class = StandardProductsPagination
    
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        elif self.action == "retrieve":
            return ProductDetailSerializer
        else:
            return ProductCreateUpdateSerializer
        
    
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return  [permissions.IsAuthenticated(), IsStaffOrReadOnly()]
        else:
            return  [permissions.AllowAny()]


    def list(self, request, *args, **kwargs):
        key = product_list_key()
        cached = product_cache.get(key)

        if cached:
            logger.info("Product list retrieved from cache successfully with key: {key}")
            return Response(cached, status=status.HTTP_200_OK)

        # get the base queryset and apply filters on them
        queryset = self.filter_queryset(self.get_queryset())

        # apply pagination configured in the pagination class
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)

        # build a paginated style response
        response_data = self.get_paginated_response(serializer.data).data

        # cache the response
        product_cache.set(key=key, value=response_data, timeout=settings.PRODUCT_LIST_CACHE_TIMEOUT)

        logger.info(f"Product list cached successfully with key: {key}")

        return Response(response_data, status=status.HTTP_200_OK)
    

        def retrieve(self, request, *args, **kwargs):
            instance = self.get_object()
            key = product_detail_key(instance.id)
            cached = product_cache.get(key)

            if cached:
                try:
                    Product.objects.filter(pk=instance.pk).update(
                        view_count=F("view_count") + 1
                    )
                    logger.info(f"Product detail retrieved from cache with key: {key}")
                except Exception as e:
                    logger.warning(
                        f"Failed to increment view count for product {instance.pk}: {str(e)}"
                    )
                return Response(cached)

            serializer = self.get_serializer(instance)
            data = serializer.data

            try:
                Product.objects.filter(pk=instance.pk).update(
                    view_count=F("view_count") + 1
                )
                logger.info(f"Product detail retrieved and cached with key: {key}")
            except Exception as e:
                logger.warning(
                    f"Failed to increment view count for product {instance.pk}: {str(e)}"
                )

            product_cache.set(key, data, timeout=settings.PRODUCT_DETAIL_CACHE_TIMEOUT)
            return Response(data, status=status.HTTP_200_OK)
    
    
class ProductReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny] 

    def get_queryset(self):
        # get the product id and filter using it
        product_id = self.kwargs.get("product_pk")

        return (
            ProductReview.objects.filter(product_id=product_id, is_approved=True)
            .select_related("user", "product")
            .order_by("-created_at")
        )
    
    def get_serializer_class(self):
        if self.action == "create":
            return ProductReviewCreateSerializer
        else:
            return ProductReviewSerializer
        
    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.AllowAny()]
        
    def perform_create(self, serializer):
        # get the user and product
        user = self.request.user
        product_id = self.kwargs.get("product_pk")

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise NotFound("Product not found")
        
        serializer.save(user=user, product=product)



        
