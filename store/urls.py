from django.urls import path
from . views import product_list
from . import views


urlpatterns = [
    path('product/', views.product_list),
]