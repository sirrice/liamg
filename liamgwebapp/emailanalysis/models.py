from django.db import models
from django.contrib.auth.models import User


# class Userdbs(models.Model):
#     user = models.ForeignKey(models.User)
#     dbname = models.CharField(max_length=30)
    

class Account(models.Model):
    class Meta:
        db_table = "accounts"

    user = models.ForeignKey(User)
    host = models.TextField()
    username = models.CharField(max_length=128)
    maxid = models.IntegerField(default=-1)

class Contact(models.Model):
    class Meta:
        db_table = "contacts"

    owner = models.ForeignKey(User)
    name = models.TextField(null=True)
    email = models.EmailField()

class Email(models.Model):
    class Meta:
        db_table = "emails"
        get_latest_by = "date"
        
    account = models.ForeignKey(Account, db_column="account")
    fr = models.ForeignKey(Contact, related_name="as_sender", db_column='fr')
    subj = models.TextField()
    date = models.DateTimeField()
    mid = models.TextField(unique=True)
    reply = models.TextField(null=True)  # references Email.mid
    multipart = models.BooleanField()

    tos = models.ManyToManyField(Contact, related_name="as_sendee", db_table='tos')
    ccs = models.ManyToManyField(Contact, related_name="as_cc", db_table='ccs')
    bccs = models.ManyToManyField(Contact, related_name="as_bcc", db_table='bccs')

class Ref(models.Model):
    class Meta:
        db_table = "refs"

    child = models.ForeignKey(Email, db_column="from", related_name="as_child")
    parent = models.TextField()
    
