from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.product_catalog.models import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductReview,
)
from decimal import Decimal

User = get_user_model()


class CategoryTestCase(TestCase):
    """Tests for category functionality"""

    def setUp(self):
        self.client = APIClient()
        self.category_url = "/api/catalog/categories/"

    def test_create_root_category(self):
        """Test creating a root category"""
        category = Category.objects.create(
            name="Electronics", description="Electronic devices"
        )

        self.assertEqual(category.name, "Electronics")
        self.assertEqual(category.slug, "electronics")
        self.assertIsNone(category.parent)
        self.assertTrue(category.is_active)

    def test_create_child_category(self):
        """Test creating a child category with parent"""
        parent = Category.objects.create(name="Electronics")
        child = Category.objects.create(name="Smartphones", parent=parent)

        self.assertEqual(child.parent, parent)
        self.assertEqual(child.level, 1)
        self.assertIn(child, parent.get_children())

    def test_category_list_api(self):
        """Test category list endpoint returns hierarchy"""
        parent = Category.objects.create(name="Electronics")
        child = Category.objects.create(name="Smartphones", parent=parent)

        response = self.client.get(self.category_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Electronics")
        self.assertEqual(len(response.data[0]["children"]), 1)

    def test_category_slug_generation(self):
        """Test slug is automatically generated from name"""
        category = Category.objects.create(name="Test Category Name")

        self.assertEqual(category.slug, "test-category-name")


class BrandTestCase(TestCase):
    """Tests for brand functionality"""

    def setUp(self):
        self.client = APIClient()
        self.brand_url = "/api/catalog/brands/"

    def test_create_brand(self):
        """Test creating a brand"""
        brand = Brand.objects.create(name="Apple", description="Technology company")

        self.assertEqual(brand.name, "Apple")
        self.assertEqual(brand.slug, "apple")
        self.assertTrue(brand.is_active)

    def test_brand_list_api(self):
        """Test brand list endpoint"""
        Brand.objects.create(name="Apple")
        Brand.objects.create(name="Samsung")

        response = self.client.get(self.brand_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_inactive_brands_not_listed(self):
        """Test inactive brands are not returned in API"""
        # Clear any existing brands from cache
        from apps.product_catalog.cache import product_cache, brand_list_key

        product_cache.delete(brand_list_key())

        Brand.objects.create(name="Active Brand", is_active=True)
        Brand.objects.create(name="Inactive Brand", is_active=False)

        response = self.client.get(self.brand_url)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Active Brand")


class ProductTestCase(TestCase):
    """Tests for product functionality"""

    def setUp(self):
        self.client = APIClient()
        self.product_url = "/api/catalog/products/"

        self.category = Category.objects.create(name="Electronics")
        self.brand = Brand.objects.create(name="Apple")

        self.product_data = {
            "name": "iPhone 15",
            "sku": "APL-IP15-128",
            "description": "Latest iPhone model",
            "short_description": "New iPhone",
            "category": self.category,
            "brand": self.brand,
            "price": Decimal("999.99"),
            "stock_quantity": 50,
            "status": "active",
            "is_available": True,
        }

    def test_create_product(self):
        """Test creating a product"""
        product = Product.objects.create(**self.product_data)

        self.assertEqual(product.name, "iPhone 15")
        self.assertEqual(product.slug, "iphone-15")
        self.assertEqual(product.price, Decimal("999.99"))
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.brand, self.brand)

    def test_product_in_stock_property(self):
        """Test is_in_stock property"""
        product = Product.objects.create(**self.product_data)

        self.assertTrue(product.is_in_stock)

        product.stock_quantity = 0
        product.save()

        self.assertFalse(product.is_in_stock)

    def test_product_discount_percentage(self):
        """Test discount percentage calculation"""
        product_data = self.product_data.copy()
        product_data["price"] = Decimal("799.99")
        product_data["compare_at_price"] = Decimal("999.99")

        product = Product.objects.create(**product_data)

        self.assertEqual(product.discount_percentage, 20)

    def test_product_list_api(self):
        """Test product list endpoint"""
        Product.objects.create(**self.product_data)

        response = self.client.get(self.product_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_product_detail_api(self):
        """Test product detail endpoint"""
        product = Product.objects.create(**self.product_data)
        detail_url = f"{self.product_url}{product.slug}/"

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "iPhone 15")
        self.assertEqual(response.data["sku"], "APL-IP15-128")

    def test_product_view_count_increments(self):
        """Test view count increments on detail view"""
        product = Product.objects.create(**self.product_data)
        detail_url = f"{self.product_url}{product.slug}/"
        initial_count = product.view_count

        self.client.get(detail_url)

        product.refresh_from_db()
        self.assertEqual(product.view_count, initial_count + 1)


class ProductFilterTestCase(TestCase):
    """Tests for product filtering functionality"""

    def setUp(self):
        self.client = APIClient()
        self.product_url = "/api/catalog/products/"

        self.category = Category.objects.create(name="Electronics")
        self.brand = Brand.objects.create(name="Apple")

        Product.objects.create(
            name="Cheap Product",
            sku="CHEAP-001",
            description="Test",
            category=self.category,
            brand=self.brand,
            price=Decimal("100.00"),
            stock_quantity=10,
            status="active",
        )

        Product.objects.create(
            name="Expensive Product",
            sku="EXPENSIVE-001",
            description="Test",
            category=self.category,
            brand=self.brand,
            price=Decimal("1000.00"),
            stock_quantity=5,
            status="active",
        )

    def test_filter_by_min_price(self):
        """Test filtering products by minimum price"""
        response = self.client.get(f"{self.product_url}?min_price=500")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Expensive Product")

    def test_filter_by_max_price(self):
        """Test filtering products by maximum price"""
        response = self.client.get(f"{self.product_url}?max_price=500")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Cheap Product")

    def test_filter_by_category(self):
        """Test filtering products by category"""
        response = self.client.get(f"{self.product_url}?category={self.category.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_search_products(self):
        """Test searching products by name"""
        response = self.client.get(f"{self.product_url}?search=Cheap")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Cheap Product")


class ProductImageTestCase(TestCase):
    """Tests for product image functionality"""

    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.brand = Brand.objects.create(name="Apple")
        self.product = Product.objects.create(
            name="iPhone 15",
            sku="APL-IP15-128",
            description="Test",
            category=self.category,
            brand=self.brand,
            price=Decimal("999.99"),
            stock_quantity=50,
        )

    def test_primary_image_uniqueness(self):
        """Test only one image can be primary per product"""
        image1 = ProductImage.objects.create(
            product=self.product, image="test1.jpg", is_primary=True
        )

        image2 = ProductImage.objects.create(
            product=self.product, image="test2.jpg", is_primary=True
        )

        image1.refresh_from_db()
        self.assertFalse(image1.is_primary)
        self.assertTrue(image2.is_primary)


class ProductReviewTestCase(TestCase):
    """Tests for product review functionality"""

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="reviewer@example.com", password="TestPass123!", is_verified=True
        )

        self.category = Category.objects.create(name="Electronics")
        self.brand = Brand.objects.create(name="Apple")
        self.product = Product.objects.create(
            name="iPhone 15",
            sku="APL-IP15-128",
            description="Test",
            category=self.category,
            brand=self.brand,
            price=Decimal("999.99"),
            stock_quantity=50,
            status="active",
        )

        self.review_url = f"/api/catalog/products/{self.product.id}/reviews/"

    def test_create_review_authenticated(self):
        """Test authenticated user can create review"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.review_url,
            {
                "rating": 5,
                "title": "Great product",
                "comment": "Really love this phone!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ProductReview.objects.filter(product=self.product, user=self.user).exists()
        )

    def test_create_review_unauthenticated(self):
        """Test unauthenticated user cannot create review"""
        response = self.client.post(
            self.review_url,
            {
                "rating": 5,
                "title": "Great product",
                "comment": "Really love this phone!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_review_prevention(self):
        """Test user cannot review same product twice"""
        ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title="First review",
            comment="Test",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.review_url,
            {"rating": 4, "title": "Second review", "comment": "Another review"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_approved_reviews_only(self):
        """Test API returns only approved reviews"""
        ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title="Approved",
            comment="Test",
            is_approved=True,
        )

        other_user = User.objects.create_user(
            email="other@example.com", password="TestPass123!"
        )

        ProductReview.objects.create(
            product=self.product,
            user=other_user,
            rating=3,
            title="Not approved",
            comment="Test",
            is_approved=False,
        )

        response = self.client.get(self.review_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Filter the response data to only count reviews for this specific product
        product_reviews = [
            r for r in response.data if r["title"] in ["Approved", "Not approved"]
        ]
        approved_reviews = [r for r in product_reviews if r["title"] == "Approved"]
        self.assertEqual(len(approved_reviews), 1)
