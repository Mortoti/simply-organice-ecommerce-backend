from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.decorators import APIView, api_view

from .models import Product, Collection
from .serializers import ProductSerializer, CollectionSerializer


# Create your views here.
@api_view(['GET'])
def product_list(request):
    queryset = Product.objects.all()
    serializer = ProductSerializer(queryset, many=True)
    return  Response(serializer.data)
@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product)
    return Response(serializer.data)
@api_view(['GET'])
def collection_list(request):
    queryset = Collection.objects.prefetch_related('products').all()
    serializer = CollectionSerializer(queryset, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def collection_detail(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    serializer = CollectionSerializer(collection)
    return Response(serializer.data)

