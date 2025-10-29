from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product, Collection, Cart, CartItem, Customer, Order

from .serializers import ProductSerializer, CollectionSerializer, CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer, CustomerSerializer, OrderSerializer, CreateOrderSerializer

from .filters import ProductFilter
from .permissions import IsAdminOrReadOnly, ViewCustomerHistoryPermissions

from .pagination import DefaultPagination




# Create your views here.
class ProductViewSet(ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'description']
    ordering_fields = ['price']
    pagination_class = DefaultPagination


class CollectionViewSet(ReadOnlyModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            return Collection.objects.prefetch_related('products').annotate(
                product_count=Count('products'))
        return queryset

class CartViewSet(GenericViewSet, RetrieveModelMixin,CreateModelMixin, DestroyModelMixin):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer

class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']
    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        else:
            return CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart_id = self.kwargs['cart_pk']).select_related('product')

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}

class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]
    @action(detail=True, permission_classes= [ViewCustomerHistoryPermissions])
    def history(self, request, pk):
        return Response("OK")

    @action(detail=False, methods=['GET', 'PUT'], permission_classes= [IsAuthenticated])
    def me(self, request):
        (customer, created) = Customer.objects.get_or_create(user_id=request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)



class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return OrderSerializer

    def get_serializer_context(self):
        return {'user_id':self.request.user.id}

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return  Order.objects.all()
        (customer_id, created) =Customer.objects.only('id').get_or_create(user_id = user.id)
        return Order.objects.filter(customer_id=customer_id)