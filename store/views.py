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
    queryset = Product.objects.all()



class CollectionViewSet(ReadOnlyModelViewSet):
    serializer_class = CollectionSerializer

    def get_queryset(self):
        if self.action == 'list':
            return Collection.objects.prefetch_related('products').annotate(
                product_count=Count('products'))
        return Collection.objects.all()





