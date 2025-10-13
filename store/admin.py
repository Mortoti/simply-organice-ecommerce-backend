from django.contrib import admin
from . import models
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
        'customer_name',
        'recipient_name',
        'recipient_number',
        'recipient_address',
        'status',
        'branch',
    )
    autocomplete_fields = ('branch',)
    list_filter = ('status',)
    search_fields = ('customer_name__istartswith', 'recipient_name__istartswith',)
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



