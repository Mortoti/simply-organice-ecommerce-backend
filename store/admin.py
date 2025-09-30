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