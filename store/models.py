from django.db import models

# Create your models here.
class Branch(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
class Collection(models.Model):
    name = models.CharField(max_length=100)
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    price = models.DecimalField(decimal_places=2, max_digits=10)
    availability = models.BooleanField()
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
class Order(models.Model):
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
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=100)
    recipient_number = models.CharField(max_length=100)
    recipient_address = models.TextField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(decimal_places=2, max_digits=10)

