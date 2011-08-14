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

# import modules for processing data
from dateutil.parser import parse
import datetime #need to get today's date as the default
import json

# add path for analysis scripts
sys.path.append(os.path.join(os.getcwd(), "../analysis"))

# import analysis modules
import topsenders
from statsbyhour import EveryoneByHour, LineData


class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField()
    sender = forms.EmailField()
    recipients = forms.EmailField()
    cc_myself = forms.BooleanField(required=False)

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100)

class CreateUserForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(max_length=100)

# index view
def index(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('emailanalysis.views.results'))
#        return render_to_response('emailanalysis/index.html')
    else:
        return HttpResponseRedirect(reverse('emailanalysis.views.login_view'))
#        return HttpResponseRedirect('emailanalysis/login')
    return render_to_response('emailanalysis/index.html')

def results(request):
    return render_to_response('emailanalysis/results.html',context_instance=RequestContext(request))

# log in view
def login_view(request):

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(username=username,password=password)
            if user is not None:
                if user.is_active:
                    login(request,user)
                    return HttpResponse('login successful') # Return success

                else:
                    return HttpResponse('user not recognized') # Return fail
            return HttpResponse('user does not exist')
        else:
            return HttpResponse('form invalid')
    else:
        form = LoginForm()
        c = {}
        c.update(csrf(request))

        return render_to_response('emailanalysis/login.html', {
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
    # db call to get data
    if datatype == 'topsenders':
        
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get ('end', None)
        top = 10       
        data = topsenders.get_top_senders(top, start, end)
        

    elif datatype == "byhour":
        req = request.REQUEST

        start = req.get('start', None)
        end = req.get('end', None)
        daysofweek = req.get('daysofweek', '')
        lat = bool(req.get('lat', False))

        if start: start = parse(start)
        if end: end = parse(end)
        if daysofweek: daysofweek = daysofweek.split(",")

        ebh = EveryoneByHour()
        queries = []
        queries.append(('y', ebh.get_sql(lat, start, end, daysofweek)))
        ld = LineData()
        data = ld.get_data(queries)

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
