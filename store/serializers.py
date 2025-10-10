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
    product = SimpleProductSerializer()
    class Meta:
        model = CartItem
        fields = ['id', 'quantity', 'products', 'total_price']
    def get_total_price(self, cart_item):
        return cart_item.quantity * cart_item.products.unit_price

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer()
    total_price = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price']
    def get_total_price(self, cart):
        return sum([item.quantity * item.product.price for item in cart.item.all()])