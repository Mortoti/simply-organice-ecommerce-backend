from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.decorators import APIView, api_view

from .models import Product, Collection
from .serializers import ProductSerializer, CollectionSerializer

from django.db.models import Count
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter



# Create your views here.
class ProductViewSet(ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter



class CollectionViewSet(ReadOnlyModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            return Collection.objects.prefetch_related('products').annotate(
                product_count=Count('products'))
        return queryset





