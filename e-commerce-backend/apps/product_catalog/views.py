from rest_framework import viewsets, status, permissions, filters, mixins
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Brand, Product, ProductReview

from .serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductReviewSerializer,
)

from .filters import ProductFilter
from .permissions import IsStaffOrReadOnly
from .pagination import StandardProductsPagination


# Create your views here.


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Get only root nodes (categories with no parent)
        return Category.objects.filter(parent__isnull=True, is_active=True)

class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset= Brand.objects.filter(is_active=True).order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]


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

        # get the base queryset and apply filters on them
        queryset = self.filter_queryset(self.get_queryset())

        # apply pagination configured in the pagination class
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)

        # build a paginated style response
        response_data = self.get_paginated_response(serializer.data).data

        return Response(response_data, status=status.HTTP_200_OK)
    
    
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
            return ProductCreateUpdateSerializer
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



        
