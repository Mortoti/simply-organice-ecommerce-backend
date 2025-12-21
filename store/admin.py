from django.contrib import admin
from .models import Collection, Product, Customer, Order, OrderItem, Cart, CartItem, Branch, BranchAccount, ProductImage

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_available', 'collection', 'is_customizable', 'customization_price', 'has_size_options']
    list_editable = ['price', 'is_available', 'is_customizable', 'customization_price', 'has_size_options']
    list_filter = ['is_available', 'collection', 'is_customizable', 'has_size_options']
    search_fields = ['name', 'description']
    inlines = [ProductImageInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'price', 'is_available', 'collection')
        }),
        ('Customization Options', {
            'fields': ('is_customizable', 'customization_price')
        }),
        ('Size Options', {
            'fields': ('has_size_options', 'available_sizes')
        }),
    )

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone', 'user']
    search_fields = ['user__first_name', 'user__last_name', 'phone']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price_at_purchase', 'with_customization', 'customization_price_at_purchase', 'selected_size']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'recipient_name', 'status', 'payment_status', 'created_at', 'branch']
    list_filter = ['status', 'payment_status', 'created_at', 'branch']
    search_fields = ['recipient_name', 'customer__user__first_name', 'customer__user__last_name']
    readonly_fields = ['created_at', 'paystack_ref', 'paystack_access_code']
    inlines = [OrderItemInline]
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer', 'recipient_name', 'recipient_number', 'recipient_address')
        }),
        ('Order Details', {
            'fields': ('status', 'payment_status', 'branch', 'created_at')
        }),
        ('Delivery Information', {
            'fields': ('delivery_date', 'delivery_time', 'secret_message')
        }),
        ('Payment Information', {
            'fields': ('paystack_ref', 'paystack_access_code')
        }),
    )

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'with_customization', 'selected_size']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['id', 'user__username']
    readonly_fields = ['id', 'created_at']
    inlines = [CartItemInline]

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_editable = ['is_active']

@admin.register(BranchAccount)
class BranchAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'branch']
    search_fields = ['user__username', 'branch__name']