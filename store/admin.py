from django.contrib import admin
from django.db.models import Count

from . import models
from django.utils.html import format_html, urlencode
from django.urls import reverse
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
@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_available')
    list_filter = ('is_available',)
    list_editable = ('price', 'is_available')
    autocomplete_fields = ('collection',)
    search_fields = ('name__istartswith',)
class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    min_num = 1
    max_num = 10
    extra = 0
    autocomplete_fields = ('product',)



@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'recipient_name',
        'recipient_number',
        'recipient_address',
        'status',
        'branch',
    )
    autocomplete_fields = ('branch',)
    list_filter = ('status',)
    search_fields = ('recipient_name__istartswith',)
    list_editable = ('status',)
    inlines = [OrderItemInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            branch_account = models.BranchAccount.objects.get(user=request.user)
            return qs.filter(branch=branch_account.branch)
        except models.BranchAccount.DoesNotExist:
            return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            try:
                branch_account = models.BranchAccount.objects.get(user=request.user)
                obj.branch = branch_account.branch
            except models.BranchAccount.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)


    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ['branch']
        return super().get_readonly_fields(request, obj)



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
