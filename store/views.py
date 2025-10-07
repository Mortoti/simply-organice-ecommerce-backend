from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.decorators import APIView, api_view

from .models import Product, Collection
from .serializers import ProductSerializer, CollectionSerializer
from rest_framework.generics import ListCreateAPIView
from django.db.models import Count



# Create your views here.
class ProductList(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product)
    return Response(serializer.data)


class CollectionList(ListCreateAPIView):
    queryset = Collection.objects.prefetch_related('products').annotate(product_count= Count('products')).all()
    serializer_class = CollectionSerializer

@api_view(['GET'])
def collection_detail(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    serializer = CollectionSerializer(collection)
    return Response(serializer.data)

