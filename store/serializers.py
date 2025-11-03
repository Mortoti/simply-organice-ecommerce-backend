from rest_framework import serializers
from .models import Product, Collection, Cart, CartItem, Customer, OrderItem, Order, Branch, ProductImage
from django.db import transaction
from .signals import order_created

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ['name', 'price', 'description', 'images', 'is_available']

class CollectionSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    product_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Collection
        fields = ['id', 'name', 'products', 'product_count']

class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price']
class CartItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    product = SimpleProductSerializer(read_only=True)
    class Meta:
        model = CartItem
        fields = ['id', 'quantity', 'product', 'total_price']
    def get_total_price(self, cart_item):
        return cart_item.quantity * cart_item.product.price

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    id = serializers.UUIDField(read_only=True)
    total_price = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price']
    def get_total_price(self, cart):
        return sum([item.quantity * item.product.price for item in cart.items.all()])

class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity']
    def validate_product_id(self, value):
        if not Product.objects.filter(pk= value).exists():
            raise serializers.ValidationError('This product does not exist')
        return value
    def save(self, **kwargs):
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']
        cart_id = self.context['cart_id']
        try:
            cart_item = CartItem.objects.get(cart_id= cart_id, product_id= product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = cart_item = CartItem.objects.create(cart_id=cart_id, **self.validated_data)
        return self.instance


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity']

class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = Customer
        fields = ['id', 'user_id', 'phone', 'birth_date']

class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    class Meta:
        model = OrderItem
        fields = ['id', 'price_at_purchase', 'product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    class Meta:
        model = Order
        fields = ['id', 'customer','recipient_name', 'items', 'recipient_number', 'recipient_address', 'branch', 'status', 'payment_status']

class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status', 'status']
class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()
    recipient_name = serializers.CharField(max_length=100)
    recipient_number = serializers.CharField(max_length=15)
    recipient_address = serializers.CharField()
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all()
    )
    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk = cart_id).exists():
            raise serializers.ValidationError("No cart with the given ID was found")
        elif CartItem.objects.filter(pk = cart_id).count()== 0:
            raise serializers.ValidationError("The Cart is Empty")
        return cart_id
    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            customer = Customer.objects.get(user_id = self.context['user_id'])
            order = Order.objects.create(
                customer=customer,
                recipient_name=self.validated_data['recipient_name'],
                recipient_number=self.validated_data['recipient_number'],
                recipient_address=self.validated_data['recipient_address'],
                branch=self.validated_data['branch']

            )
            cart_items = CartItem.objects.select_related('product').filter(cart_id = cart_id)

            order_items =[
                OrderItem(
                    order= order,
                    product = item.product,
                    price_at_purchase = item.product.price,
                    quantity = item.quantity
                )for item in cart_items
            ]

            OrderItem.objects.bulk_create(order_items)
            Cart.objects.filter(pk=cart_id).delete()

            order_created.send_robust(self.__class__, order=order)

            return order