from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.decorators import APIView, api_view

from .models import Product, Collection
from .serializers import ProductSerializer, CollectionSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.db.models import Count



# Create your views here.
class ProductList(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
class ProductDetail(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer



class CollectionList(ListAPIView):
    queryset = Collection.objects.prefetch_related('products').annotate(product_count= Count('products')).all()
    serializer_class = CollectionSerializer

class CollectionDetail(RetrieveAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer


