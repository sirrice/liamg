# Create your views here.

# import python libraries
import sys,os

# import django modules
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.core.context_processors import csrf
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django import forms

# models
from emailanalysis.models import Userdbs

# import modules for processing data
from dateutil.parser import parse
import datetime #need to get today's date as the default
import json

# add path for analysis scripts
sys.path.append(os.path.join(os.getcwd(), "../analysis"))
sys.path.append(os.path.join(os.getcwd(), ".."))

# import analysis modules
import topsenders
from statsbyhour import *
from timeline import *
from contacts import Contacts
import getdata


#getdata.setup_db(conn)


class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField()
    sender = forms.EmailField()
    recipients = forms.EmailField()
    cc_myself = forms.BooleanField(required=False)

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'size':'25','style':'font-size:18px'}),max_length=100)
    password = forms.CharField(widget=forms.PasswordInput(render_value=False, attrs={'size':'25','style':'font-size:18px'}),max_length=100)
    defaultdb = forms.NullBooleanField()

class CreateUserForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(max_length=100)

# index view
# redirects to login if not logged in
# otherwise, shows results
@login_required(login_url='/emailanalysis/login/')
def index(request):
    # if logged in, redirect to results view
    return HttpResponseRedirect(reverse('emailanalysis.views.results'))

@login_required(login_url='/emailanalysis/login/')
def results(request):
    return render_to_response('emailanalysis/results.html',context_instance=RequestContext(request))


def pie(request):
    return render_to_response('emailanalysis/pie.html',context_instance=RequestContext(request))

# log in view
def login_view(request):

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            defaultdb = form.cleaned_data['defaultdb']
            if defaultdb:
                # log in as default
                username = "default@default.com"
                user = authenticate(username=username,password='default')

                # create default user if it doesn't exist
                if not user:
                    user = User.objects.create_user(username, username, "default")
                    user = authenticate(username=username,password='default')

                    userdb = Userdbs(username=username)
                    userdb.save() # creates userdb.id
                    dbname = 'mail.db'
                    userdb.dbname = dbname
                    userdb.save()
                    
                login(request,user)
                return HttpResponseRedirect("/emailanalysis/results/")

            else:
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']

                # check if gmail password is valid
                try:
                    getdata.authenticate_login('imap.googlemail.com',username,password)
                except:
                    # not valid
                    return HttpResponse('user/password combo invalid')

                # check if user in db
                user = authenticate(username=username,password='')
                if user is not None:
                    if user.is_active:
                        login(request,user)
                        # should redirect user to the results page
                        return HttpResponseRedirect("/emailanalysis/results/")

                    else:
                        return HttpResponse('user not recognized') # Return fail
                # user doesn't exist: create user
                # download data, return results page
                else:
                    user = User.objects.create_user(username,'','')
                    user = authenticate(username=username,password='')
                    login(request,user)
                    # create database name for user
                    userdb = Userdbs(username=username)
                    userdb.save() # creates userdb.id
                    dbname = 'user{0}.db'.format(userdb.id)
                    userdb.dbname = dbname
                    userdb.save()
                    print dbname
                    conn = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES)
                    print conn
                    getdata.setup_db(conn)
                    getdata.download_headers('imap.googlemail.com',username,password,conn)
                    os.system('./analyzedb.sh {0}'.format(dbname))
                    conn.close()

                    # redirect to results page?
                    return HttpResponse('data downloaded')
        else:
            return HttpResponse('form invalid')
    else:
        form = LoginForm(initial={'username':'default@default.com','password':'default','defaultdb':True})
        c = {}
        c.update(csrf(request))

        return render_to_response('emailanalysis/home.html', {
            'form': form,
            },context_instance=RequestContext(request))

# create new user
def create_user(request):

    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # create user
            user = User.objects.create_user(username,email,password)

            return HttpResponse('user created')
        else:
            return HttpResponse('form invalid')
    else:
        form = CreateUserForm()
        c = {}
        c.update(csrf(request))

        return render_to_response('emailanalysis/newuser.html', {
            'form': form,
            },context_instance=RequestContext(request))
    

# log out user
def logout_view(request):
    logout(request)
    return HttpResponse('user logged out')

# get json data
@login_required(login_url='/emailanalysis/login/')
def getjson(request, datatype):
    req = request.REQUEST

    start = req.get('start', None)
    end = req.get('end', None)
    daysofweek = req.get('daysofweek', '')
    reply = req.get('reply', None)
    lat = bool(req.get('lat', False))
    email = req.get('email', None)
    granularity = req.get('granularity', None)

    if start: start = parse(start)
    if end: end = parse(end)
    if daysofweek: daysofweek = daysofweek.split(",")
    if reply is not None: reply = bool(reply)

    curruser = Userdbs.objects.get(username=request.user)
    print request.user
    print curruser.dbname

    conn = sqlite3.connect(curruser.dbname, detect_types=sqlite3.PARSE_DECLTYPES)

    # db call to get data
    if datatype == 'topsenders':
        
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get ('end', None)
        top = 10       
        data = topsenders.get_top_senders(top, start, end, conn)
        

    elif datatype == "byhour":
        ebh = RepliesByHour()
        queries = []
        print "EMAIL", email
        queries.append(('y', ebh.get_sql(lat=lat, reply=reply, start=start, end=end,
                                         daysofweek=daysofweek, email=email)))
        ld = LineData()
        data = ld.get_data(queries, conn)

    elif datatype == "contacts":
        contacts = Contacts()
        data = contacts.get_data(conn)

    elif datatype == "getlatency":
        bd = ByDay()
        queries = []
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end,
                                        granularity=granularity, email=email)))
        ld = BDLineData()
        data = ld.get_data(queries, conn, 0, granularity=granularity, start=start, end=end)

    elif datatype == "getcount":
        bd = ByDayNorm()
        queries = []
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end,
                                        granularity=granularity, email=email)))
        ld = BDLineData()
        data = ld.get_data(queries, conn, 1, granularity=granularity, start=start, end=end)

    else:
        return HttpResponse('json call not recognized')

    # return data as json
    return HttpResponse(json.dumps(data), mimetype="application/json")

@login_required
def sendmail(request):

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            sender = form.cleaned_data['sender']
            cc_myself = form.cleaned_data['cc_myself']

            recipients = [form.cleaned_data['recipients']]
            if cc_myself:
                recipients.append(sender)



            email = EmailMessage(subject, message, sender, recipients)
            email.attach_file('images/Lydia.jpg')
            email.send()
#            send_mail(subject, message, sender, recipients)
            #return HttpResponseRedirect('/thanks/') # Redirect after POST
        

    #send_mail('Welcome!','this is inbox doctor. i will tell you when you suck at responding to emails. inbox.dr was taken, so that\'s why it\'s inbox.doctor.', 'inbox.doctor@gmail.com', ['zhenya.gu@gmail.com','sirrice@gmail.com', 'ravdawg@gmail.com','farm.cp@gmail.com','melty710@gmail.com','jeezumpeez@gmail.com'], fail_silently=False)

            return HttpResponse('mail sent')

    else:
        form = ContactForm()
        c = {}
        c.update(csrf(request))

        return render_to_response('emailanalysis/sendmail.html', {
            'form': form,
            },context_instance=RequestContext(request))
