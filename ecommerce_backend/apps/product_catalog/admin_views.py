import logging
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Brand, Product, ProductImage, ProductReview
from .permissions import IsStaffOnly
from .admin_serializers import (
    AdminCategorySerializer,
    AdminBrandSerializer,
    AdminProductSerializer,
    AdminProductImageSerializer,
    AdminProductReviewSerializer,
)


logger = logging.getLogger(__name__)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAuthenticated, IsStaffOnly]



class AdminBrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by("name")
    serializer_class = AdminBrandSerializer
    permission_classes = [IsAuthenticated, IsStaffOnly]


class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related(
        "brand", 
        "category"
        ).prefetch_related(
        "images"
    )

    serializer_class = AdminProductSerializer
    permission_classes = [IsAuthenticated, IsStaffOnly]


class AdminProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = AdminProductImageSerializer
    permission_classes = [IsAuthenticated, IsStaffOnly]


class AdminProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.select_related("product", "user")
    serializer_class = AdminProductReviewSerializer
    permission_classes = [IsAuthenticated, IsStaffOnly]

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsStaffOnly] )
    def approve(self, request, pk=None):
        """Approve a product review."""
        review = self.get_object()
        review.is_approved = True
        review.save(update_fields=["is_approved"])

        serializer = self.get_serializer(review)

        return Response(
            {"message": "Review approved successfully", "review": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsStaffOnly])
    def reject(self, request, pk=None):
        """Reject a product review."""
        review = self.get_object()
        review.is_approved = False
        review.save(update_fields=["is_approved"])

        serializer = self.get_serializer(review)

        return Response(
            {"message": "Review rejected successfully", "review": serializer.data},
            status=status.HTTP_200_OK,
        )
