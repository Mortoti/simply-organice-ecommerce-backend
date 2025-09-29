from django.db import models

# Create your models here.
class Branch(models.Model):
    name = models.CharField(max_length=100)
class Collection(models.Model):
    name = models.CharField(max_length=100)
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField()
    price = models.DecimalField(decimal_places=2, max_digits=10)
    availability = models.BooleanField()
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

