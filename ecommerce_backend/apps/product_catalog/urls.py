from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    BrandViewSet,
    ProductViewSet,
    ProductReviewViewSet
)


router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"products", ProductViewSet, basename="product")


reviews_list = ProductReviewViewSet.as_view({
    "get": "list",
    "post": "create"
})


urlpatterns = [
    path("", include(router.urls)),
    
    path("products/<uuid:product_pk>/reviews/", reviews_list, name="product-reviews"),
]
