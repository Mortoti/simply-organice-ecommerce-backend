from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.decorators import APIView, api_view

from .models import Product, Collection
from .serializers import ProductSerializer, CollectionSerializer

from django.db.models import Count
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet



# Create your views here.
class ProductViewSet(ReadOnlyModelViewSet):

    serializer_class = ProductSerializer
    def get_queryset(self):
        queryset = Product.objects.all()
        collection_id = self.request.query_params.get("collection_id")
        if collection_id is not None:
            queryset = queryset.filter(collection_id= collection_id)
        return queryset



class CollectionViewSet(ReadOnlyModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            return Collection.objects.prefetch_related('products').annotate(
                product_count=Count('products'))
        return queryset





