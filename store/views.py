from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Product, Collection, Cart

from .serializers import ProductSerializer, CollectionSerializer, CartSerializer

from .filters import ProductFilter

from .pagination import DefaultPagination




# Create your views here.
class ProductViewSet(ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price']
    pagination_class = DefaultPagination


class CollectionViewSet(ReadOnlyModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            return Collection.objects.prefetch_related('products').annotate(
                product_count=Count('products'))
        return queryset

class CartViewSet(GenericViewSet, RetrieveModelMixin, CreateModelMixin):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer



