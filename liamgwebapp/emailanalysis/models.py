from django.db import models

# Create your models here.
class Userdbs(models.Model):
    username = models.EmailField(max_length=75)
    dbname = models.CharField(max_length=30)
