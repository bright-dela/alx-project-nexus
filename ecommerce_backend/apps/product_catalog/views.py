import logging
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
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

# Create your views here.


logger = logging.getLogger(__name__)


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


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True).order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]


@method_decorator(cache_page(60 * 5), name="list")
@method_decorator(cache_page(60 * 10), name="retrieve")
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

        return [permission() for permission in permission_classes]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            Product.objects.filter(pk=instance.pk).update(
                view_count=F("view_count") + 1
            )
        except Exception as e:
            logger.warning(
                f"Failed to increment view count for product {instance.pk}: {str(e)}"
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def add_review(self, request, pk=None):
        product = self.get_object()

        serializer = ProductReviewCreateSerializer(
            data=request.data, context={"request": request, "product": product}
        )

        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        response_serializer = ProductReviewSerializer(
            review, context={"request": request}
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
