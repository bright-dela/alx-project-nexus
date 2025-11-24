from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg
from django.urls import reverse
from mptt.admin import DraggableMPTTAdmin
from .models import Category, Brand, Product, ProductImage, ProductReview


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    """Admin interface for hierarchical category management with drag-and-drop."""
    
    list_display = [
        'tree_actions',
        'indented_title',
        'is_active',
        'product_count',
        'created_at'
    ]
    
    list_display_links = ['indented_title']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'get_full_path']
    
    mptt_level_indent = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'parent', 'description', 'image')
        }),
        ('Hierarchy', {
            'fields': ('get_full_path',),
            'description': 'Shows the full path of this category in the hierarchy'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_count(self, obj):
        count = obj.products.count()
        if count > 0:
            app_label = obj._meta.app_label
            url = reverse(f'admin:{app_label}_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} products</a>', url, count)
        return '0 products'
    
    product_count.short_description = 'Products'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin interface for brand management."""
    
    list_display = ['name', 'logo_preview', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'logo_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Media', {
            'fields': ('logo', 'logo_preview')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 200px;" />', obj.logo.url)
        return 'No logo'
    
    logo_preview.short_description = 'Logo Preview'
    
    def product_count(self, obj):
        count = obj.products.count()
        if count > 0:
            app_label = obj._meta.app_label
            url = reverse(f'admin:{app_label}_product_changelist') + f'?brand__id__exact={obj.id}'
            return format_html('<a href="{}">{} products</a>', url, count)
        return '0 products'
    
    product_count.short_description = 'Products'


class ProductImageInline(admin.TabularInline):
    """Inline interface for managing product images within product admin."""
    
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'display_order', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px;" />', obj.image.url)
        return 'No image'
    
    image_preview.short_description = 'Preview'


class ProductReviewInline(admin.TabularInline):
    """Inline interface for viewing product reviews within product admin."""
    
    model = ProductReview
    extra = 0
    fields = ['user', 'rating', 'title', 'is_verified_purchase', 'is_approved', 'created_at']
    readonly_fields = ['user', 'rating', 'title', 'created_at']
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for product management with comprehensive features."""
    
    list_display = [
        'name', 
        'sku', 
        'category', 
        'brand', 
        'formatted_price', 
        'stock_status', 
        'status', 
        'is_featured',
        'view_count',
        'average_rating'
    ]
    
    list_filter = [
        'status', 
        'is_featured', 
        'is_available', 
        'category', 
        'brand', 
        'created_at',
        'currency'
    ]
    
    search_fields = ['name', 'sku', 'description', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'view_count', 
        'is_in_stock', 
        'is_low_stock',
        'discount_percentage',
        'average_rating',
        'review_count'
    ]
    
    inlines = [ProductImageInline, ProductReviewInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'short_description', 'description')
        }),
        ('Categorization', {
            'fields': ('category', 'brand')
        }),
        ('Pricing', {
            'fields': ('price', 'currency', 'compare_at_price', 'cost_price', 'discount_percentage')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold', 'is_in_stock', 'is_low_stock')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'is_available', 'is_featured', 'published_at')
        }),
        ('Specifications', {
            'fields': ('specifications',),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('view_count', 'average_rating', 'review_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_active', 'make_draft', 'mark_as_featured', 'unmark_as_featured']
    
    def formatted_price(self, obj):
        if obj.discount_percentage > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} {}</span> '
                '<span style="text-decoration: line-through; color: gray;">{} {}</span> '
                '<span style="color: green;">(-{}%)</span>',
                obj.currency, obj.price,
                obj.currency, obj.compare_at_price,
                obj.discount_percentage
            )
        return f'{obj.currency} {obj.price}'
    
    formatted_price.short_description = 'Price'
    
    def stock_status(self, obj):
        if obj.stock_quantity == 0:
            color = 'red'
            status = 'Out of Stock'
        elif obj.is_low_stock:
            color = 'orange'
            status = f'Low Stock ({obj.stock_quantity})'
        else:
            color = 'green'
            status = f'In Stock ({obj.stock_quantity})'
        
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, status)
    
    stock_status.short_description = 'Stock'
    
    def average_rating(self, obj):
        avg = obj.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg']
        if avg:
            stars = '★' * int(avg) + '☆' * (5 - int(avg))
            return format_html('<span style="color: #f39c12;">{}</span> ({:.1f})', stars, avg)
        return 'No ratings'
    
    average_rating.short_description = 'Rating'
    
    def review_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()
    
    review_count.short_description = 'Approved Reviews'
    
    def make_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} products marked as active.')
    
    make_active.short_description = 'Mark selected products as active'
    
    def make_draft(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} products marked as draft.')
    
    make_draft.short_description = 'Mark selected products as draft'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    
    mark_as_featured.short_description = 'Mark as featured'
    
    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} products unmarked as featured.')
    
    unmark_as_featured.short_description = 'Remove featured status'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Admin interface for standalone product image management."""
    
    list_display = ['product', 'image_thumbnail', 'alt_text', 'is_primary', 'display_order', 'created_at']
    list_filter = ['is_primary', 'created_at', 'product']
    search_fields = ['product__name', 'alt_text']
    readonly_fields = ['created_at', 'image_preview']
    
    fieldsets = (
        ('Product', {
            'fields': ('product',)
        }),
        ('Image', {
            'fields': ('image', 'image_preview', 'alt_text')
        }),
        ('Display', {
            'fields': ('is_primary', 'display_order')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return 'No image'
    
    image_thumbnail.short_description = 'Thumbnail'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 500px;" />', obj.image.url)
        return 'No image'
    
    image_preview.short_description = 'Full Preview'


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """Admin interface for product review management and moderation."""
    
    list_display = [
        'product',
        'user',
        'rating_display',
        'title',
        'is_verified_purchase',
        'is_approved',
        'created_at'
    ]
    
    list_filter = [
        'rating',
        'is_verified_purchase',
        'is_approved',
        'created_at',
        'product'
    ]
    
    search_fields = ['product__name', 'user__email', 'title', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Review Details', {
            'fields': ('product', 'user', 'rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'unapprove_reviews']
    
    def rating_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #f39c12; font-size: 16px;">{}</span>', stars)
    
    rating_display.short_description = 'Rating'
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    
    approve_reviews.short_description = 'Approve selected reviews'
    
    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews unapproved.')
    
    unapprove_reviews.short_description = 'Unapprove selected reviews'