import pickle
from django.db import models




class StockProduct(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False, unique=True)
    price = models.FloatField(default=0)
    stock = models.IntegerField(default=0)


class SaleProduct(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False, unique=True)
    price = models.FloatField(null=False)
    base_items = models.ManyToManyField(StockProduct, null=True)
    description = models.TextField(null=True, blank=True)


class Employee(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    cpf = models.CharField(max_length=15, null=False, blank=False, unique=True)
    date_of_birth = models.DateField()
    gender = models.IntegerField()
    role = models.CharField(max_length=80, null=False, blank=False)
    admission_date = models.DateField()
    age = models.IntegerField()
    address = models.TextField()


class Customer(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    rg = models.CharField(max_length=20, null=False, blank=False, unique=True)
    date_of_birth = models.DateField()
    age = models.IntegerField()
    gender = models.IntegerField()
    visits = models.IntegerField(default=0)


class CardControl(models.Model):
    code = models.IntegerField(unique=True)
    products = models.BinaryField(default=pickle.dumps({}))
    date_in = models.DateTimeField()
    date_out = models.DateTimeField(null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=False)
    total_amount = models.FloatField(default=0.0)
