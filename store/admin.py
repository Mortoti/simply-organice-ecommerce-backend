# In store/admin.py

from django.contrib import admin
from django.db.models import Count
from core.tasks import send_email_task  # <-- Import the task
from django.conf import settings
from . import models
from django.utils.html import format_html, urlencode
from django.urls import reverse

# --- Imports to fix linter warnings ---
from django.db.models.base import Model
from django.forms.models import ModelForm
from django.http.request import HttpRequest


# ------------------------------------

# Register your models here.
@admin.register(models.Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name__istartswith',)
    ordering = ('name',)
    list_filter = ('is_active',)


@admin.register(models.BranchAccount)
class BranchAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'branch')


@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_filter = ('name',)
    search_fields = ('name__istartswith',)
    list_per_page = 12


class ProductImageInline(admin.TabularInline):
    model = models.ProductImage
    readonly_fields = ['thumbnail']

    @staticmethod
    def thumbnail(instance):
        if instance.image.name != '':
            return format_html(
                '<img src="{}" style="width: 100px; border-radius: 5px;" />',
                instance.image.url
            )
        return ''


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_available')
    list_filter = ('is_available',)
    inlines = [ProductImageInline]
    list_editable = ('price', 'is_available')
    autocomplete_fields = ('collection',)
    search_fields = ('name__istartswith',)


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0
    autocomplete_fields = ('product',)
    readonly_fields = ('product', 'quantity', 'price_at_purchase')

    def has_add_permission(self, request, obj=None):
        """Allow adding items only when creating a new order"""
        return obj is None

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting items from existing orders"""
        return obj is None

    def has_change_permission(self, request, obj=None):
        """Prevent editing items in existing orders"""
        return obj is None


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'recipient_name',
        'recipient_number',
        'recipient_address',
        'colored_status',
        'colored_payment_status',
        'branch',
    )

    @admin.display(description='Status')
    def colored_status(self, obj):
        colors = {
            'Pending': 'orange',
            'Shipped': 'blue',
            'Completed': 'green',
            'Cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status
        )

    @admin.display(description='Payment')
    def colored_payment_status(self, obj):
        colors = {
            'Pending': 'orange',
            'Completed': 'green',
            'Failed': 'red',
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.payment_status
        )

    autocomplete_fields = ('branch',)
    list_filter = ('status', 'payment_status', 'created_at', 'branch')
    search_fields = ('recipient_name__istartswith', 'id', 'paystack_ref')
    inlines = [OrderItemInline]
    list_per_page = 10
    readonly_fields = ('paystack_ref', 'paystack_access_code', 'created_at')

    # Show these fields in the detail view
    fieldsets = (
        ('Order Information', {
            'fields': ('customer', 'recipient_name', 'recipient_number', 'recipient_address', 'branch')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Payment Details', {
            'fields': ('paystack_ref', 'paystack_access_code', 'created_at'),
            'classes': ('collapse',)  # Make this section collapsible
        }),
    )

    def get_queryset(self, request):
        """
        Filter orders based on:
        1. Branch (if user is not superuser)
        2. Payment status (show only completed payments by default)
        """
        qs = super().get_queryset(request)

        # Branch filtering (your existing logic)
        if not request.user.is_superuser:
            try:
                branch_account = models.BranchAccount.objects.get(user=request.user)
                qs = qs.filter(branch=branch_account.branch)
            except models.BranchAccount.DoesNotExist:
                return qs.none()

        # Payment status filtering - show only paid orders by default
        # Unless the admin has specifically filtered by payment_status
        if 'payment_status' not in request.GET:
            # No payment_status filter selected, so show only completed payments
            qs = qs.filter(payment_status=models.Order.PAYMENT_COMPLETED)

        return qs

    def save_model(self, request: HttpRequest, obj: models.Order, form: ModelForm, change: bool):
        # Your branch logic is correct
        if not request.user.is_superuser:
            try:
                branch_account = models.BranchAccount.objects.get(user=request.user)
                obj.branch = branch_account.branch
            except models.BranchAccount.DoesNotExist:
                pass

        # This is the logic that calls the task
        if change and 'status' in form.changed_data:
            # Check if the status is one we want to send an email for
            if (obj.status == models.Order.STATUS_SHIPPED or
                    obj.status == models.Order.STATUS_COMPLETED):
                try:
                    # Only send email if Redis/Celery is available
                    send_email_task.delay(order_id=obj.id)
                except Exception as e:
                    # Log the error but don't block the save
                    print(f"Failed to queue email for order {obj.id}: {str(e)}")

        # We call the parent save_model at the end
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.extend(['paystack_ref', 'paystack_access_code', 'payment_status', 'created_at'])

        if not request.user.is_superuser:
            readonly.append('branch')

        return readonly

    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion of orders with completed payments.
        Only unpaid orders can be deleted, and only by superusers.
        """
        if obj is None:
            return request.user.is_superuser

        # Never allow deletion of paid orders
        if obj.payment_status == models.Order.PAYMENT_COMPLETED:
            return False

        # Allow superusers to delete unpaid orders only
        return request.user.is_superuser


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'orders']
    list_per_page = 10
    list_select_related = ['user']
    autocomplete_fields = ['user']
    ordering = ['user__first_name', 'user__last_name']
    search_fields = ['first_name__istartswith', 'last_name__istartswith']

    @admin.display(ordering='orders_count')
    def orders(self, customer):
        url = (
                reverse('admin:store_order_changelist')
                + '?'
                + urlencode({
            'customer__id': str(customer.id)
        }))

        return format_html('<a href="{}">{} Orders</a>', url, customer.orders_count)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            orders_count=Count('order')
        )