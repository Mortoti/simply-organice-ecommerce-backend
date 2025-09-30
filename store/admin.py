from django.contrib import admin
from . import models
# Register your models here.
@admin.register(models.Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
    list_filter = ('is_active',)
@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_filter = ('name',)
    search_fields = ('name',)
    list_per_page = 10
@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_available')
    list_filter = ('is_available',)
    autocomplete_fields = ('collection',)
@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer_name',
                    'recipient_name',
                    'recipient_number',
                    'recipient_address',
                    'status',
                    )
    autocomplete_fields = ('branch',)
    list_filter = ('status',)
    search_fields = ('customer_name','recipient_name',)
