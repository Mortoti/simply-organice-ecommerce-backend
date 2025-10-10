from django.urls import path

from . import views
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register('products', views.ProductViewSet, basename='products')
router.register('collections', views.CollectionViewSet)
router.register('carts', views.CartViewSet)


urlpatterns = router.urls