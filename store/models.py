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
    is_customizable = models.BooleanField(default=False)
    customization_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    has_size_options = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['collection']),
            models.Index(fields=['price']),
            models.Index(fields=['is_customizable']),
            models.Index(fields=['customization_price']),
        ]

    def __str__(self):
        return self.name


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    size_name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ['product', 'size_name']
        indexes = [
            models.Index(fields=['product', 'size_name']),
        ]
        ordering = ['price']

    def __str__(self):
        return f"{self.product.name} - {self.size_name} (${self.price})"
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
    PAYMENT_FAILED = 'Failed'
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
        return f'Order {self.pk} - {self.recipient_name}'

    def save(self, *args, **kwargs):
        # Check if this is an update (not a new order)
        if self.pk:
            # Get the old status from database
            old_order = Order.objects.get(pk=self.pk)
            old_status = old_order.status

            # If status changed, send email
            if old_status != self.status:
                # Import here to avoid circular import
                from core.tasks import send_email_task

                # Save first, then send email
                super().save(*args, **kwargs)

                # Send email asynchronously using Celery
                send_email_task.delay(self.id)
                return

        # If it's a new order or status didn't change, just save normally
        super().save(*args, **kwargs)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_at_purchase = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    with_customization = models.BooleanField(default=False)
    customization_price_at_purchase = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    selected_size = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'Order {self.pk} - {self.product.name}'
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)  # ADD THIS
    created_at = models.DateTimeField(auto_now_add=True)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    with_customization = models.BooleanField(default=False)
    selected_size = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = [['cart', 'product', 'with_customization', 'selected_size']]

    @property
    def total_price(self):
        base_price = self.product.price * self.quantity
        if self.with_customization and self.product.is_customizable:
            base_price += (self.product.customization_price * self.quantity)
        return base_price






