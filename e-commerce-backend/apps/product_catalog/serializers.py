from rest_framework import serializers

from .models import Category, Brand, Product, ProductImage, ProductReview

from django.db.models import Avg


class CategorySerializer(serializers.ModelSerializer):

    children = serializers.SerializerMethodField()

    class Meta:
        model: Category
        fields = ["id", "name", "slug", "description", "children"]

    def get_children(self, object):

        children = object.get_children()
        # return an empty list if category has no nested categories
        if not children:
            return []
        else:
            return CategorySerializer(children, many=True, context=self.context).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo", "description"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "display_order"]


class ProductListSerializer(serializers.ModelSerializer):

    primary_image = serializers.SerializerMethodField()
    is_in_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    brand = BrandSerializer(read_only=True)

    class Meta:
        models = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "currency",
            "compare_at_price",
            "discount_percentage",
            "is_in_stock",
            "brand",
            "primary_image",
        ]

    def get_primary_image(self, object):
        primary = object.images.filter(is_primary=True).first()

        if not primary:
            return None

        if not hasattr(primary, "image") or not primary.image:
            return None

        request = self.context.get("request")

        url = primary.image.url

        if request:
            return request.build_absolute_uri(url)
        else:
            return url


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    is_in_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "short_description",
            "price",
            "currency",
            "compare_at_price",
            "discount_percentage",
            "is_in_stock",
            "stock_quantity",
            "specifications",
            "brand",
            "category",
            "images",
            "average_rating",
            "reviews",
            "created_at",
            "updated_at",
            "published_at",
        ]

    def get_reviews(self, object):
        queryset = object.reviews.filter(is_approved=True).order_by("-created_at")

        return ProductReviewSerializer(queryset, many=True, context=self.context).data
    
    def get_average_rating(self, object):
        result = object.reviews.filter(is_approved=True).aggregate(avg=Avg("rating"))

        if result["avg"] is not None:
            return float(result["avg"])
        else: 
            return None
        

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
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
            "published_at",
        ]
        read_only_fields = ["slug"]
    
    def validate(self, attrs):
        # validate prices (shouldn't be negative)
        price = attrs.get("price")
        
        if price is not None and price < 0:
            raise serializers.ValidationError({
                "price": "Price must be greater than or equal to 0."
            })
        
        compare_at_price = attrs.get("compare_at_price")
        
        if compare_at_price is not None and price is not None:
            if compare_at_price < price:
                raise serializers.ValidationError({
                    "compare_at_price": "Compare at price must be greater than or equal to price."
                })
        
        return attrs


class ProductReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            "id",
            "user",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "is_approved",
            "created_at"
        ]



class ProductReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = ["rating", "title", "comment"]
    
    # validate rating (must be between 1-5)
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )
        return value
    
    def create(self, validated_data):
        # get user and product from the request object
        request = self.context.get("request")

        user = request.user
        product = self.context.get("product")
        
        return ProductReview.objects.create(
            product=product,
            user=user,
            **validated_data
        )
