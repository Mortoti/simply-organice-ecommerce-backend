from rest_framework import serializers
from .models import Product, Collection, Cart, CartItem, Customer, OrderItem, Order, Branch, ProductImage
from django.db import transaction
from .signals import order_created, order_created


class ProductImageSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        product_id = self.context['product_id']
        return ProductImage.objects.create(product_id=product_id, **validated_data)

    class Meta:
        model = ProductImage
        fields = ['id', 'image']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    collection = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'description', 'images', 'is_available', 'collection', 'is_customizable',
                  'customization_price', 'has_size_options', 'available_sizes']


class CollectionSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'products', 'product_count']


class SimpleProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'image', 'is_customizable', 'customization_price', 'has_size_options',
                  'available_sizes']

    def get_image(self, obj):
        if hasattr(obj, 'images') and obj.images.exists():
            first_image = obj.images.first()
            if first_image and first_image.image:
                return first_image.image.url
        elif hasattr(obj, 'image') and obj.image:
            return obj.image.url
        return None


class CartItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    product = SimpleProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'quantity', 'product', 'total_price', 'with_customization', 'selected_size']

    def get_total_price(self, cart_item):
        base_price = cart_item.quantity * cart_item.product.price
        if cart_item.with_customization and cart_item.product.is_customizable:
            base_price += (cart_item.product.customization_price * cart_item.quantity)
        return base_price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    id = serializers.UUIDField(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at']

    def get_total_price(self, cart):
        total = 0
        for item in cart.items.all():
            base_price = item.quantity * item.product.price
            if item.with_customization and item.product.is_customizable:
                base_price += (item.product.customization_price * item.quantity)
            total += base_price
        return total


class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    with_customization = serializers.BooleanField(default=False)
    selected_size = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity', 'with_customization', 'selected_size']

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('This product does not exist')
        return value

    def save(self, **kwargs):
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']
        with_customization = self.validated_data.get('with_customization', False)
        selected_size = self.validated_data.get('selected_size')
        cart_id = self.context['cart_id']

        try:
            cart_item = CartItem.objects.get(
                cart_id=cart_id,
                product_id=product_id,
                with_customization=with_customization,
                selected_size=selected_size
            )
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(cart_id=cart_id, **self.validated_data)
        return self.instance


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity', 'with_customization', 'selected_size']


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'user_id', 'phone', 'birth_date']


class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()

    class Meta:
        model = OrderItem
        fields = ['id', 'price_at_purchase', 'product', 'quantity', 'with_customization',
                  'customization_price_at_purchase', 'selected_size']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'customer',
            'recipient_name',
            'recipient_number',
            'recipient_address',
            'branch',
            'status',
            'payment_status',
            'created_at',
            'paystack_ref',
            'paystack_access_code',
            'secret_message',
            'delivery_date',
            'delivery_time',
            'items'
        ]


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status', 'status']


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()
    recipient_name = serializers.CharField(max_length=100)
    recipient_number = serializers.CharField(max_length=15)
    recipient_address = serializers.CharField()
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    secret_message = serializers.CharField(required=False, allow_blank=True)
    delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_time = serializers.TimeField(required=False, allow_null=True)

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError("No cart with the given ID was found")
        elif CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError("The Cart is Empty")
        return cart_id

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            customer = Customer.objects.get(user_id=self.context['user_id'])
            order = Order.objects.create(
                customer=customer,
                recipient_name=self.validated_data['recipient_name'],
                recipient_number=self.validated_data['recipient_number'],
                recipient_address=self.validated_data['recipient_address'],
                branch=self.validated_data['branch'],
                secret_message=self.validated_data.get('secret_message', ''),
                delivery_date=self.validated_data.get('delivery_date'),
                delivery_time=self.validated_data.get('delivery_time')
            )
            cart_items = CartItem.objects.select_related('product').filter(cart_id=cart_id)

            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    price_at_purchase=item.product.price,
                    quantity=item.quantity,
                    with_customization=item.with_customization,
                    customization_price_at_purchase=item.product.customization_price if item.with_customization else 0,
                    selected_size=item.selected_size
                ) for item in cart_items
            ]

            OrderItem.objects.bulk_create(order_items)
            Cart.objects.filter(pk=cart_id).delete()

            order_created.send_robust(self.__class__, order=order)

            return order


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'is_active']
        read_only_fields = ['id']