from rest_framework import serializers
from .models import Category, Brand, Product, ProductImage, ProductReview




class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug"]



class AdminBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = [
            "id",
            "name",
            "slug",
            "logo",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug"]


class AdminProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "id",
            "product",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "created_at",
        ]



class AdminProductSerializer(serializers.ModelSerializer):
    images = AdminProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "short_description",
            "category",
            "brand",
            "price",
            "currency",
            "compare_at_price",
            "cost_price",
            "stock_quantity",
            "low_stock_threshold",
            "status",
            "is_featured",
            "is_available",
            "specifications",
            "meta_title",
            "meta_description",
            "view_count",
            "created_at",
            "updated_at",
            "published_at",
            "images",
        ]
        read_only_fields = ["slug", "view_count"]



class AdminProductReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "product",
            "product_name",
            "user",
            "user_email",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "is_approved",
            "created_at",
            "updated_at",
        ]
