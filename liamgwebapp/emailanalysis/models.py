from django.db import models
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.conf import settings
import psycopg2 as pg
import sys
sys.path.append("../")
from getdata import AsyncDownload


# class Userdbs(models.Model):
#     user = models.ForeignKey(models.User)
#     dbname = models.CharField(max_length=30)
    

class Account(models.Model):
    class Meta:
        db_table = "accounts"

    user = models.ForeignKey(User)
    host = models.TextField()
    username = models.CharField(max_length=128)
    max_dl_mid = models.IntegerField(default=-1)
    maxlatid = models.IntegerField(default=0)
    max_mid = models.IntegerField(default=0)
    last_refresh = models.DateTimeField(auto_now_add=True)
    refreshing = models.BooleanField(default=False)
    
    @transaction.commit_manually
    def check_for_new(self, password):
    
        # wrap in xact
        if self.refreshing:
            return False

        conn = pg.connect(database=settings.DATABASES['default']['NAME'],
                          user=settings.DATABASES['default']['USER'],
                          password=settings.DATABASES['default']['PASSWORD'])
        ad = AsyncDownload(self, password, conn, 100)
        ad.start()
        return True

    def __unicode__(self):
        return "%s@%s" % (self.user.username, self.host)

        
        

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

    #URGENT: Need to fix this so that imapid will accept multiple emails with the same ID but have different account numbers.
    imapid = models.IntegerField(unique=True)
    mid = models.TextField(unique=True)
    reply = models.TextField(null=True)  # references Email.mid
    multipart = models.BooleanField()

    tos = models.ManyToManyField(Contact, related_name="as_sendee", db_table='tos')
    ccs = models.ManyToManyField(Contact, related_name="as_cc", db_table='ccs')
    bccs = models.ManyToManyField(Contact, related_name="as_bcc", db_table='bccs')

class Content(models.Model):
    class Meta:
        db_table = "contents"

    email = models.OneToOneField(Email, db_column="emailid", related_name="content",
                                 to_field="imapid")
    text = models.TextField() 

class Ref(models.Model):
    class Meta:
        db_table = "refs"

    child = models.ForeignKey(Email, db_column="from", related_name="as_child")
    parent = models.TextField()
    

class Latency(models.Model):
    class Meta:
        db_table = "latencies"
        unique_together = (('owner', 'replyemail', 'origemail'),)

    owner = models.ForeignKey(Account, db_column="account")
    replier = models.ForeignKey(Contact, related_name="reply",  db_column="replier")
    sender = models.ForeignKey(Contact, related_name="sender", db_column="sender")
    replyemail = models.ForeignKey(Email, related_name="lat_reply", db_column="replyemail")
    origemail = models.ForeignKey(Email, related_name="lat_orig", db_column="origemail")
    replydate = models.DateTimeField( db_column="replydate")
    origdate = models.DateTimeField( db_column="origdate")
    lat = models.FloatField( db_column="lat" )
    
    #do we need to add another field here to get the time difference? I think we had something in sqlite for this called 'lat'
