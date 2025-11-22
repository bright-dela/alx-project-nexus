import logging
from django.db.models import F
from rest_framework import viewsets, mixins, status, permissions, filters

from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Brand, Product, ProductReview
from .serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductReviewSerializer,
    ProductReviewCreateSerializer,
)
from .filters import ProductFilter
from .pagination import StandardResultsSetPagination

from .cache import (
    product_cache,
    product_list_key,
    product_detail_key,
    category_tree_key,
)

# Create your views here.


logger = logging.getLogger(__name__)


CATEGORY_TREE_CACHE_TIMEOUT = 60 * 60 * 12
PRODUCT_LIST_CACHE_TIMEOUT = 60 * 5
PRODUCT_DETAIL_CACHE_TIMEOUT = 60 * 10


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access for anyone, write only for staff users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        is_staff = getattr(request.user, "is_staff", False)

        return bool(request.user and request.user.is_authenticated and is_staff)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.get_root_nodes()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        key = category_tree_key()
        cached = product_cache.get(key)

        if cached:
            logger.info("cached data retrieved successfully with key: {key}")

            return Response(cached)

        serializer = self.get_serializer(self.get_queryset(), many=True)
        data = serializer.data
        product_cache.set(key, data, timeout=CATEGORY_TREE_CACHE_TIMEOUT)

        logger.info(f"category tree cache set successfully with key: {key}")

        return Response(data)


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True).order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        key = "brand_list:v1"

        cached = product_cache.get(key)

        if cached:
            logger.info("cached data retrieved successfully with key: {key}")

            return Response(cached)

        serializer = self.get_serializer(self.get_queryset(), many=True)
        data = serializer.data
        product_cache.set(key, data, timeout=60 * 60)
        logger.info("brand cache set successfully with key: {key}")
        return Response(data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("brand", "category").prefetch_related(
        "images"
    )

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer

        if self.action == "retrieve":
            return ProductDetailSerializer

        return ProductCreateUpdateSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]
        else:
            permission_classes = [permissions.AllowAny]

        # Get a list of permissions depending on the action
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        key = product_list_key(request)
        cached = product_cache.get(key)

        if cached:
            logger.info(f"cached data retrieved successfully with key: {key}")
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        response_data = self.get_paginated_response(serializer.data).data
        product_cache.set(key, response_data, timeout=PRODUCT_LIST_CACHE_TIMEOUT)

        logger.info(f"product list cache set successfully with key: {key}")
        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        key = product_detail_key(instance.id)

        cached = product_cache.get(key)

        if cached:
            Product.objects.filter(pk=instance.id).update(
                view_count=F("view_count") + 1
            )

            try:
                Product.objects.filter(pk=instance.pk).update(
                    view_count=F("view_count") + 1
                )
                logger.info(
                    f"product detail retrieved successfully with key: {key} and view count updated to {instance.view_count}"
                )

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
            logger.info(
                f"product detail retrieved successfully with key: {key} and view count updated to {instance.view_count}"
            )

        except Exception as e:
            logger.warning(
                f"Failed to increment view count for product {instance.pk}: {str(e)}"
            )

        product_cache.set(key, data, timeout=PRODUCT_DETAIL_CACHE_TIMEOUT)
        return Response(data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def add_review(self, request, pk=None):
        product = self.get_object()

        serializer = ProductReviewCreateSerializer(
            data=request.data, 
            context={"request": request, 
            "product": product}
        )

        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        response_serializer = ProductReviewSerializer(
            review, 
            context={"request": request}
        )

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)



class ProductReviewViewSet(
    mixins.ListModelMixin, 
    mixins.CreateModelMixin, 
    viewsets.GenericViewSet
):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        product_id = self.kwargs.get("product_pk")

        return ProductReview.objects.filter(
            product_id=product_id, 
            is_approved=True
        ).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ProductReviewCreateSerializer
        return ProductReviewSerializer

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        product_id = self.kwargs.get("product_pk")

        try:
            product = Product.objects.get(pk=product_id)
            
        except Product.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Product not found")

        serializer.save(user=self.request.user, product=product)
