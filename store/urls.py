from django.urls import path, include
from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register('products', views.ProductViewSet, basename='products')
router.register('collections', views.CollectionViewSet)
router.register('carts', views.CartViewSet, basename='cart')  # ADD basename='cart'
router.register('customers', views.CustomerViewSet)
router.register('orders', views.OrderViewSet, basename='orders')
router.register('branches', views.BranchViewSet, basename='branches')

products_router = routers.NestedDefaultRouter(router, 'products', lookup='product')
products_router.register('images', views.ProductImageViewSet, basename='product-images')

carts_router = routers.NestedDefaultRouter(router, 'carts', lookup='cart')
carts_router.register('items', views.CartItemViewSet, basename='cart-items')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(products_router.urls)),
    path('', include(carts_router.urls)),

    # Payment routes
    path('orders/<int:order_id>/initialize-payment/',
         views.InitializePaymentView.as_view(),
         name='initialize-payment'),
    path('payments/verify/',
         views.VerifyPaymentView.as_view(),
         name='verify-payment'),
    path('payments/webhook/',
         views.PaystackWebhookView.as_view(),
         name='paystack-webhook'),
]