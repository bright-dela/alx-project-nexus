import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):

    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")

    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    category = django_filters.UUIDFilter(field_name="category__id")

    brand = django_filters.UUIDFilter(field_name="brand__id")

    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    status = django_filters.ChoiceFilter(
        field_name="status", 
        choices=Product.STATUS_CHOICES
    )

    is_featured = django_filters.BooleanFilter(field_name="is_featured")

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
        fields = [
            "min_price",
            "max_price",
            "category",
            "brand",
            "in_stock",
            "search",
            "status",
            "is_featured",
        ]
