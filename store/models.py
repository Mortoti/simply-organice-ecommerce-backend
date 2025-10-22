from django.core.validators import MinValueValidator
from django.db import models
from uuid import uuid4

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
    image = models.ImageField(upload_to='products/')
    price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_available = models.BooleanField()
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='products')
    def __str__(self):
        return self.name
class Customer(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)


    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        ordering = ['first_name', 'last_name']
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
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=15)
    recipient_name = models.CharField(max_length=100)
    recipient_number = models.CharField(max_length=15)
    recipient_address = models.TextField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(max_length=25, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
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







