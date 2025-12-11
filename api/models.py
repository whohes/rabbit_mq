from django.db import models


class Dealer(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    address = models.CharField(max_length=100)
    area = models.CharField(max_length=50)
    rating = models.DecimalField(max_digits=3, decimal_places=1)

    class Meta:
        db_table = "dealers"


class Car(models.Model):
    firm = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    power = models.IntegerField()
    color = models.CharField(max_length=30)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE)

    class Meta:
        db_table = "cars"


