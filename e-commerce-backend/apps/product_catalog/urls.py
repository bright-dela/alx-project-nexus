from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    CategoryViewSet,
    BrandViewSet,
    ProductReviewViewSet,
    ProductViewSet,
)

router = DefaultRouter()

router.register(r"categories", CategoryViewSet, basename="category")

router.register(r"brands", BrandViewSet, basename="brand")

router.register(r"products", ProductViewSet, basename="product")

# nested routing
products_router = routers.NestedSimpleRouter(router, r"products", lookup="product")

products_router.register(r"reviews", ProductReviewViewSet, basename="product-reviews")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(products_router.urls)),
]