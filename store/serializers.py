from rest_framework import serializers
from .models import Product, Collection, Cart, CartItem


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'price', 'description', 'image', 'is_available']
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
