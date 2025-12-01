"""
Django Management Command to Load Products from DummyJSON API
Place this file in: apps/product_catalog/management/commands/load_products_dummyjson.py

DummyJSON provides 100 products with:
- High-quality images (multiple per product)
- Detailed descriptions
- Real brands
- Ratings and reviews
- Stock information
- Free to use

Usage:
    python manage.py load_products_dummyjson --limit 30
"""

import requests
import urllib.request
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.utils.text import slugify
from apps.product_catalog.models import Category, Brand, Product, ProductImage
from apps.authentication.models import User


class Command(BaseCommand):
    help = "Load real products with images from DummyJSON API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing products before loading new ones",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=30,
            help="Number of products to load (max 100)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Product.objects.all().delete()
            ProductImage.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ Data cleared"))

        limit = min(options["limit"], 100)
        self.stdout.write(f"Fetching {limit} products from DummyJSON API...")

        try:
            # Fetch products
            response = requests.get(f"https://dummyjson.com/products?limit={limit}")
            response.raise_for_status()
            data = response.json()
            products_data = data["products"]

            self.stdout.write(
                self.style.SUCCESS(f"✓ Found {len(products_data)} products")
            )

            # Create categories and brands
            category_mapping = self._create_categories(products_data)
            brand_mapping = self._create_brands(products_data)

            # Create products
            self._create_products(products_data, category_mapping, brand_mapping)

            self.stdout.write(self.style.SUCCESS("✓ Products loaded successfully!"))
            self._print_summary()

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"✗ Error fetching data: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {e}"))

    def _create_categories(self, products_data):
        """Create nested categories from product data using MPTT"""
        self.stdout.write("Creating nested categories...")

        # Get unique categories
        categories = set(prod["category"] for prod in products_data)

        category_mapping = {}

        # Define hierarchical category structure
        # Format: {api_category: (display_name, parent_slug, description)}
        category_hierarchy = {
            # Electronics category tree
            "smartphones": (
                "Smartphones",
                "electronics",
                "Latest smartphones and mobile devices",
            ),
            "laptops": (
                "Laptops",
                "electronics",
                "High-performance laptops and notebooks",
            ),
            # Beauty & Personal Care tree
            "fragrances": (
                "Fragrances",
                "beauty-personal-care",
                "Premium perfumes and fragrances",
            ),
            "skincare": (
                "Skincare",
                "beauty-personal-care",
                "Skincare and beauty products",
            ),
            # Home & Living tree
            "groceries": ("Groceries", "home-living", "Fresh groceries and food items"),
            "home-decoration": (
                "Home Decoration",
                "home-living",
                "Home decor and accessories",
            ),
            "furniture": ("Furniture", "home-living", "Modern furniture for your home"),
            "lighting": ("Lighting", "home-living", "Modern lighting solutions"),
            # Fashion category tree
            "tops": ("Tops", "womens-fashion", "Fashionable tops and shirts"),
            "womens-dresses": (
                "Dresses",
                "womens-fashion",
                "Elegant dresses for women",
            ),
            "womens-shoes": ("Shoes", "womens-fashion", "Stylish footwear for women"),
            "womens-watches": (
                "Watches",
                "womens-fashion",
                "Elegant watches for women",
            ),
            "womens-bags": ("Bags", "womens-fashion", "Fashionable bags and purses"),
            "womens-jewellery": (
                "Jewellery",
                "womens-fashion",
                "Beautiful jewelry pieces",
            ),
            # Men's Fashion tree
            "mens-shirts": ("Shirts", "mens-fashion", "Quality shirts for men"),
            "mens-shoes": ("Shoes", "mens-fashion", "Comfortable shoes for men"),
            "mens-watches": ("Watches", "mens-fashion", "Premium watches for men"),
            # Accessories tree
            "sunglasses": (
                "Sunglasses",
                "accessories",
                "Trendy sunglasses and eyewear",
            ),
            # Automotive tree
            "automotive": (
                "Auto Parts",
                "automotive",
                "Automotive parts and accessories",
            ),
            "motorcycle": ("Motorcycle", "automotive", "Motorcycle gear and parts"),
        }

        # Parent categories (these will be created as intermediate nodes)
        parent_categories = {
            "electronics": ("Electronics", None, "Electronic devices and gadgets"),
            "beauty-personal-care": (
                "Beauty & Personal Care",
                None,
                "Beauty and personal care products",
            ),
            "home-living": ("Home & Living", None, "Everything for your home"),
            "womens-fashion": ("Women's Fashion", "fashion", "Fashion items for women"),
            "mens-fashion": ("Men's Fashion", "fashion", "Fashion items for men"),
            "fashion": ("Fashion", None, "Clothing, shoes and accessories"),
            "accessories": ("Accessories", "fashion", "Fashion accessories and more"),
            "automotive": ("Automotive", None, "Vehicles, parts and accessories"),
        }

        # Store created categories for reference
        created_categories = {}

        # Step 1: Create root category
        root = Category.objects.create(
            name="All Categories",
            slug="all-categories",
            description="Browse all product categories",
            is_active=True,
        )
        created_categories["root"] = root
        self.stdout.write("  ✓ Created root: All Categories")

        # Step 2: Create parent categories (level 1 and level 2)
        # First pass: Create level 1 parents (those with parent=None)
        for slug, (name, parent_slug, desc) in parent_categories.items():
            if parent_slug is None:
                parent_cat = Category.objects.create(
                    name=name, slug=slug, description=desc, parent=root, is_active=True
                )
                created_categories[slug] = parent_cat
                self.stdout.write(f"  ✓ Created parent: {name}")

        # Second pass: Create level 2 parents (those with parent_slug set)
        for slug, (name, parent_slug, desc) in parent_categories.items():
            if parent_slug is not None and slug not in created_categories:
                parent_cat = Category.objects.create(
                    name=name,
                    slug=slug,
                    description=desc,
                    parent=created_categories.get(parent_slug, root),
                    is_active=True,
                )
                created_categories[slug] = parent_cat
                self.stdout.write(f"  ✓ Created sub-parent: {name}")

        # Step 3: Create leaf categories (actual product categories)
        for cat_name in sorted(categories):
            if cat_name in category_hierarchy:
                display_name, parent_slug, description = category_hierarchy[cat_name]
                parent = created_categories.get(parent_slug, root)
            else:
                # Fallback for unknown categories
                display_name = cat_name.replace("-", " ").title()
                description = f"Browse our {display_name.lower()} collection"
                parent = root

            category = Category.objects.create(
                name=display_name,
                slug=cat_name,
                description=description,
                parent=parent,
                is_active=True,
            )
            category_mapping[cat_name] = category
            created_categories[cat_name] = category

            # Show hierarchy in output
            hierarchy_path = category.get_full_path()
            self.stdout.write(f"  ✓ Created: {hierarchy_path}")

        return category_mapping

    def _create_brands(self, products_data):
        """Create brands from product data"""
        self.stdout.write("Creating brands...")

        # Get unique brands
        brands = set(prod["brand"] for prod in products_data if prod.get("brand"))

        brand_mapping = {}

        for brand_name in sorted(brands):
            brand = Brand.objects.create(
                name=brand_name,
                slug=slugify(brand_name),
                description=f"Quality products from {brand_name}",
                is_active=True,
            )
            brand_mapping[brand_name] = brand
            self.stdout.write(f"  ✓ Created brand: {brand_name}")

        return brand_mapping

    def _create_products(self, products_data, category_mapping, brand_mapping):
        """Create products with images"""
        self.stdout.write("Creating products...")

        for prod_data in products_data:
            try:
                # Get category
                category = category_mapping.get(prod_data["category"])
                if not category:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Skipping: Unknown category")
                    )
                    continue

                # Get brand
                brand = brand_mapping.get(prod_data.get("brand"))

                # Convert price to GHS (1 USD = 12 GHS approximately)
                usd_price = Decimal(str(prod_data["price"]))
                ghs_price = (usd_price * Decimal("12")).quantize(Decimal("0.01"))

                # Calculate discounted price if discount exists
                discount_percent = prod_data.get("discountPercentage", 0)
                compare_price = None
                if discount_percent > 0:
                    compare_price = (
                        ghs_price / (1 - Decimal(str(discount_percent)) / 100)
                    ).quantize(Decimal("0.01"))

                # Generate SKU
                sku = prod_data.get("sku", f"PROD-{prod_data['id']:04d}")

                # Determine stock status
                stock = prod_data.get("stock", 0)
                status = "active" if stock > 0 else "out_of_stock"

                # Create product
                product = Product.objects.create(
                    name=prod_data["title"][:300],
                    slug=slugify(prod_data["title"][:280]) + f"-{prod_data['id']}",
                    sku=sku,
                    description=prod_data["description"],
                    short_description=(
                        prod_data["description"][:200] + "..."
                        if len(prod_data["description"]) > 200
                        else prod_data["description"]
                    ),
                    category=category,
                    brand=brand,
                    price=ghs_price,
                    currency="GHS",
                    compare_at_price=compare_price,
                    cost_price=(ghs_price * Decimal("0.65")).quantize(Decimal("0.01")),
                    stock_quantity=stock,
                    low_stock_threshold=prod_data.get("minimumOrderQuantity", 5),
                    status=status,
                    is_featured=(prod_data.get("rating", 0) >= 4.5),
                    is_available=(stock > 0),
                    specifications={
                        "rating": prod_data.get("rating", 0),
                        "brand": prod_data.get("brand", ""),
                        "warranty": prod_data.get("warrantyInformation", ""),
                        "shipping": prod_data.get("shippingInformation", ""),
                        "return_policy": prod_data.get("returnPolicy", ""),
                        "weight": prod_data.get("weight", 0),
                        "dimensions": prod_data.get("dimensions", {}),
                    },
                    meta_title=prod_data["title"][:200],
                    meta_description=prod_data["description"][:300],
                )

                # Download and attach images
                images = prod_data.get("images", [])
                for idx, image_url in enumerate(
                    images[:4]
                ):  # Limit to 4 images per product
                    self._download_product_image(product, image_url, idx)

                self.stdout.write(
                    f"  ✓ Created: {product.name[:50]}... ({len(images)} images)"
                )

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Error creating product: {e}")
                )
                continue

    def _download_product_image(self, product, image_url, index):
        """Download product image and attach to product"""
        try:
            # Download image
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(urllib.request.urlopen(image_url).read())
            img_temp.flush()

            # Create ProductImage
            file_name = f"{product.slug}-{index}.jpg"
            product_image = ProductImage.objects.create(
                product=product,
                alt_text=f"{product.name} - Image {index + 1}",
                is_primary=(index == 0),
                display_order=index,
            )
            product_image.image.save(file_name, File(img_temp), save=True)

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"    ⚠ Could not download image {index}: {e}")
            )

    def _print_summary(self):
        """Print summary of loaded data with category tree"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("DATABASE SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Categories: {Category.objects.count()}")
        self.stdout.write(
            f"  - Root categories: {Category.objects.filter(level=0).count()}"
        )
        self.stdout.write(f"  - Level 1: {Category.objects.filter(level=1).count()}")
        self.stdout.write(f"  - Level 2: {Category.objects.filter(level=2).count()}")
        self.stdout.write(f"  - Level 3: {Category.objects.filter(level=3).count()}")
        self.stdout.write(f"Brands: {Brand.objects.count()}")
        self.stdout.write(f"Products: {Product.objects.count()}")
        self.stdout.write(f"Product Images: {ProductImage.objects.count()}")
        self.stdout.write(
            f"Featured Products: {Product.objects.filter(is_featured=True).count()}"
        )
        self.stdout.write(
            f'In Stock: {Product.objects.filter(status="active").count()}'
        )
        self.stdout.write(
            f'Out of Stock: {Product.objects.filter(status="out_of_stock").count()}'
        )
        self.stdout.write("=" * 60)

        # Display category tree structure
        self.stdout.write("\n" + self.style.SUCCESS("CATEGORY TREE STRUCTURE"))
        self.stdout.write("=" * 60)
        root_cats = Category.objects.filter(level=0)
        for root in root_cats:
            self._print_category_tree(root, indent=0)
        self.stdout.write("=" * 60 + "\n")

    def _print_category_tree(self, category, indent=0):
        """Recursively print category tree"""
        prefix = "  " * indent + ("└─ " if indent > 0 else "")
        product_count = category.products.count()
        count_str = f" ({product_count} products)" if product_count > 0 else ""
        self.stdout.write(f"{prefix}{category.name}{count_str}")

        # Print children
        for child in category.get_children():
            self._print_category_tree(child, indent + 1)
