from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminCategoryViewSet,
    AdminBrandViewSet,
    AdminProductViewSet,
    AdminProductImageViewSet,
    AdminProductReviewViewSet,
)


router = DefaultRouter()

router.register(r"categories", AdminCategoryViewSet, basename="admin-categories")

router.register(r"brands", AdminBrandViewSet, basename="admin-brands")

router.register(r"products", AdminProductViewSet, basename="admin-products")

router.register(r"product-images", AdminProductImageViewSet, basename="admin-product-images")

router.register(r"reviews", AdminProductReviewViewSet, basename="admin-reviews")


urlpatterns = router.urls
