from django.core.validators import MinValueValidator
from django.db import models
from uuid import uuid4
from django.contrib import admin
from .validators import validate_file_size

from django.conf import settings

# Create your models here.
class Branch(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name
class BranchAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.branch.name}"
class Collection(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_available = models.BooleanField()
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='products')

    class Meta:
        indexes = [
            models.Index(fields=['is_available']),  # Speed up filtering
            models.Index(fields=['collection']),  # Speed up collection queries
            models.Index(fields=['price']),  # Speed up price sorting
        ]
    def __str__(self):
        return self.name
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='products/',
        validators= [validate_file_size])
class Customer(models.Model):
    phone = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    @admin.display(ordering='user__first_name')
    def first_name(self):
        return self.user.first_name
    @admin.display(ordering='user__last_name')
    def last_name(self):
        return self.user.last_name
    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'

    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        permissions = [
            ('view_history', 'Can view history')
        ]
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    STATUS_PENDING = 'Pending'
    STATUS_SHIPPED = 'Shipped'
    STATUS_COMPLETED = 'Completed'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )
    PAYMENT_PENDING = 'Pending'
    PAYMENT_COMPLETED = 'Completed'
    PAYMENT_FAILED= 'Failed'
    PAYMENT_STATUS_CHOICES = (
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_COMPLETED, 'Completed'),
        (PAYMENT_FAILED, 'Failed'),
    )
    recipient_name = models.CharField(max_length=100)
    recipient_number = models.CharField(max_length=15)
    recipient_address = models.TextField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(max_length=25, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    paystack_ref = models.CharField(max_length=100, blank=True, null=True)
    paystack_access_code = models.CharField(max_length=100, blank=True, null=True)
    secret_message = models.TextField(blank=True, null=True, help_text="Private message from customer")
    delivery_date = models.DateField(blank=True, null=True, help_text="Preferred delivery date")
    delivery_time = models.TimeField(blank=True, null=True, help_text="Preferred delivery time")
    class Meta:
        permissions = [
            ('cancel_order', 'Can cancel order')
        ]
        indexes = [
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]
    def __str__(self):
        return  f'Order {self.pk} - {self.recipient_name}'
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)] )
    price_at_purchase = models.DecimalField(decimal_places=2, max_digits=10, default=0)

    def __str__(self):
        return f'Order {self.pk} - {self.product.name}'
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    class Meta:
        unique_together = [['cart', 'product']]







