from django.db import models

# Create your models here.
class Branch(models.Model):
    name = models.CharField(max_length=100)
class Collection(models.Model):
    name = models.CharField(max_length=100)
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
