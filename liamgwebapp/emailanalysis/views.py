# Create your views here.

# import django modules
import sys,os
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.core.context_processors import csrf

from dateutil.parser import parse
import datetime #need to get today's date as the default
import json

# append db dir to python path
sys.path.append(os.path.join(os.getcwd(), "../analysis"))
print sys.path

import topsenders
from statsbyhour import EveryoneByHour, LineData
from timeline import *
from contacts import Contacts
from django import forms

class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField()
    sender = forms.EmailField()
    recipients = forms.EmailField()
    cc_myself = forms.BooleanField(required=False)

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100)

# index view
def index(request):
    if request.user.is_autheticated():
        print 'user kewl'
    else:
        return HttpResponseRedirect(reverse('emailanalysis.views.login_view'))
#        return HttpResponseRedirect('emailanalysis/login')
    return render_to_response('emailanalysis/index.html')

# log in view
def login_view(request):

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(username=username,password=password)
            if user is not None:
                if user.is_active:
                    login(request,user)
                    return HttpResponseRedirect('/login successful/') # Redirect after POST
                else:
                    return HttpResponseRedirect('/user not recognized/') # Redirect after POST
            
            return HttpResponse('mail sent')

    else:
        form = LoginForm()
        c = {}
        c.update(csrf(request))

        return render_to_response('emailanalysis/sendmail.html', {
            'form': form,
            },context_instance=RequestContext(request))


# log out user
def logout_view(request):
    logout(request)

# get json data
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

    
    # db call to get data
    if datatype == 'topsenders':
        
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get ('end', None)
        top = 10       
        data = topsenders.get_top_senders(top, start, end)
        

    elif datatype == "byhour":
        ebh = EveryoneByHour()
        queries = []
        queries.append(('y', ebh.get_sql(lat, start, end, daysofweek)))
        ld = LineData()
        data = ld.get_data(queries)

    elif datatype == "contacts":
        contacts = Contacts()
        data = contacts.get_data()

    elif datatype == "getlatency":
        bd = ByDay()
        queries = []
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end,
                                        granularity=granularity, email=email)))
        ld = BDLineData()
        data = ld.get_data(queries, 0, granularity=granularity)
    elif datatype == "getcount":
        bd = ByDay()
        queries = []
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end,
                                        granularity=granularity, email=email)))
        ld = BDLineData()
        data = ld.get_data(queries, 1, granularity=granularity)

    else:
        return HttpResponse('json call not recognized')

    # return data as json
    return HttpResponse(json.dumps(data), mimetype="application/json")


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
