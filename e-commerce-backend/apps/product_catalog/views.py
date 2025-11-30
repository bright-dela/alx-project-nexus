from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions, filters, mixins
from rest_framework.exceptions import NotFound

from django_filters.rest_framework import DjangoFilterBackend

from django.conf import settings
from django.db.models import F

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

from .cache import (
    product_cache,
    product_list_key,
    product_detail_key,
    category_tree_key,
    brand_list_key,
)

from .response_utils import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
)

import logging

logger = logging.getLogger(__name__)



class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        # Get only root nodes (categories with no parent)
        return Category.objects.filter(parent__isnull=True, is_active=True)

    def list(self, request, *args, **kwargs):
        key = category_tree_key()
        cached = product_cache.get(key)

        if cached:
            logger.info(
                f"Category tree retrieved from cache successfully with key: {key}"
            )
            # Return cached data with standardized format
            return success_response(
                message="Categories retrieved successfully",
                data={"categories": cached, "count": len(cached)},
                metadata={"cached": True}
            )

        serializer = self.get_serializer(self.get_queryset(), many=True)

        data = serializer.data

        product_cache.set(
            key=key, value=data, 
            timeout=settings.CATEGORY_TREE_CACHE_TIMEOUT
        )

        logger.info(f"Category tree cached successfully with key: {key}")

        return success_response(
            message="Categories retrieved successfully",
            data={"categories": data, "count": len(data)},
            metadata={"cached": False}
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return success_response(
                message="Category retrieved successfully",
                data=serializer.data
            )
        
        except Category.DoesNotExist:
            return not_found_response("Category not found")



class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True).order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        key = brand_list_key()
        cached = product_cache.get(key)

        if cached:
            logger.info(f"Brand list retrieved from cache successfully with key: {key}")

            return success_response(
                message="Brands retrieved successfully",
                data={"brands": cached, "count": len(cached)},
                metadata={"cached": True}
            )

        serializer = self.get_serializer(self.get_queryset(), many=True)

        data = serializer.data

        product_cache.set(key, data, timeout=60 * 60)

        logger.info(f"Brand list cached successfully with key: {key}")
        
        return success_response(
            message="Brands retrieved successfully",
            data={"brands": data, "count": len(data)},
            metadata={"cached": False}
        )


    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return success_response(
                message="Brand retrieved successfully",
                data=serializer.data
            )
        
        except Brand.DoesNotExist:
            return not_found_response("Brand not found")


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("brand", "category").prefetch_related(
        "images"
    )

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
            return [permissions.IsAuthenticated(), IsStaffOrReadOnly()]
        else:
            return [permissions.AllowAny()]

    def list(self, request, *args, **kwargs):
        key = product_list_key(request)
        cached = product_cache.get(key)

        if cached:
            logger.info(f"Product list retrieved from cache successfully with key: {key}")
            # Cached data already has pagination structure
            return success_response(
                message="Products retrieved successfully",
                data=cached,
                metadata={"cached": True}
            )

        # Get the base queryset and apply filters on them
        queryset = self.filter_queryset(self.get_queryset())

        # Apply pagination configured in the pagination class
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)

        # Build a paginated style response
        paginated_response = self.get_paginated_response(serializer.data)
        
        # Extract pagination data
        response_data = {
            "results": serializer.data,
            "count": paginated_response.data.get("count"),
            "next": paginated_response.data.get("next"),
            "previous": paginated_response.data.get("previous"),
        }

        # Cache the response with appropriate timeout
        product_cache.set(
            key=key, 
            value=response_data, 
            timeout=settings.PRODUCT_LIST_CACHE_TIMEOUT
        )

        logger.info(f"Product list cached successfully with key: {key}")

        return success_response(
            message="Products retrieved successfully",
            data=response_data,
            metadata={"cached": False}
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

        except Product.DoesNotExist:
            return not_found_response("Product not found")

        key = product_detail_key(instance.id)
        cached = product_cache.get(key)

        if cached:
            # Increment view count even when serving from cache
            try:
                Product.objects.filter(pk=instance.pk).update(
                    view_count=F("view_count") + 1
                )

                logger.info(f"Product detail retrieved from cache with key: {key}")

            except Exception as e:
                logger.warning(
                    f"Failed to increment view count for product {instance.pk}: {str(e)}"
                )
            
            return success_response(
                message="Product retrieved successfully",
                data=cached,
                metadata={"cached": True}
            )

        serializer = self.get_serializer(instance)
        data = serializer.data

        # Increment view count when generating fresh response
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

        return success_response(
            message="Product retrieved successfully",
            data=data,
            metadata={"cached": False}
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        self.perform_create(serializer)
        
        return success_response(
            message="Product created successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        
        try:
            instance = self.get_object()
        except Product.DoesNotExist:
            return not_found_response("Product not found")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        self.perform_update(serializer)

        return success_response(
            message="Product updated successfully",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Product.DoesNotExist:
            return not_found_response("Product not found")

        self.perform_destroy(instance)
        
        return success_response(
            message="Product deleted successfully",
            data={"id": str(instance.id)}
        )


class ProductReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny]
    queryset = ProductReview.objects.all()
    pagination_class = StandardProductsPagination

    def get_product(self):
        slug = (
            self.kwargs.get("product_slug") or
            self.kwargs.get("product_pk") or
            self.kwargs.get("product_product_slug")
        )

        # print(slug)

        if not slug:
            raise NotFound("Product slug not found")

        return get_object_or_404(Product, slug=slug)

    def get_queryset(self):
        product = self.get_product()

        return ProductReview.objects.filter(
            product=product,
            is_approved=True
        ).select_related("user", "product")

    def get_serializer_class(self):
        return (
            ProductReviewCreateSerializer
            if self.action == "create"
            else ProductReviewSerializer
        )

    def get_permissions(self):
        return (
            [permissions.IsAuthenticated()]
            if self.action == "create"
            else [permissions.AllowAny()]
        )

    def list(self, request, *args, **kwargs):
        try:
            product = self.get_product()
        except Product.DoesNotExist:
            return not_found_response("Product not found")

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)
        paginated_response = self.get_paginated_response(serializer.data)

        response_data = {
            "reviews": serializer.data,
            "count": paginated_response.data.get("count"),
            "next": paginated_response.data.get("next"),
            "previous": paginated_response.data.get("previous"),
        }

        return success_response(
            message="Product reviews retrieved successfully",
            data=response_data
        )

    def create(self, request, *args, **kwargs):
        try:
            product = self.get_product()
        except Product.DoesNotExist:
            return not_found_response("Product not found")

        user = request.user

        # Check if user already reviewed this product
        if ProductReview.objects.filter(product=product, user=user).exists():
            return error_response(
                error_type="duplicate_review",
                message="You have already reviewed this product",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        serializer.save(product=product, user=user)

        return success_response(
            message="Review submitted successfully. It will be visible after approval.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )