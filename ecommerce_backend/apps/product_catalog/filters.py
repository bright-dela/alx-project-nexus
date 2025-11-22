import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    """
    Custom filter set for Product queryset filtering.
    Provides filters for price range, category, brand, stock status, and more.
    """
    
    min_price = django_filters.NumberFilter(
        field_name="price", 
        lookup_expr="gte",
        label="Minimum Price"
    )

    max_price = django_filters.NumberFilter(
        field_name="price", 
        lookup_expr="lte",
        label="Maximum Price"
    )

    category = django_filters.UUIDFilter(
        field_name="category__id",
        label="Category"
    )

    brand = django_filters.UUIDFilter(
        field_name="brand__id",
        label="Brand"
    )

    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock",
        label="In Stock"
    )

    status = django_filters.ChoiceFilter(
        field_name="status", 
        choices=Product.STATUS_CHOICES,
        label="Status"
    )

    is_featured = django_filters.BooleanFilter(
        field_name="is_featured",
        label="Featured Products"
    )

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products based on stock availability.
        Returns products with stock > 0 and is_available = True.
        """
        if value:
            return queryset.filter(stock_quantity__gt=0, is_available=True)
        return queryset

    class Meta:
        model = Product
        fields = ['status', 'is_featured']