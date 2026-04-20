from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, DigitalKey, Review, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'caption', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'category', 'price', 'is_active', 'available_keys', 'created_at']
    list_filter = ['is_active', 'platform', 'category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['tags']
    inlines = [ProductImageInline]


@admin.register(DigitalKey)
class DigitalKeyAdmin(admin.ModelAdmin):
    list_display = ['product', 'key', 'is_used']
    list_filter = ['is_used', 'product']
    search_fields = ['key']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'price', 'quantity', 'key']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'is_paid', 'created_at']
    list_filter = ['is_paid']
    inlines = [OrderItemInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'rating', 'created_at']
    list_filter = ['rating', 'product']