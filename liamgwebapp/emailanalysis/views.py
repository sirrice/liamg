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
from emailanalysis.models import *

# models
#from emailanalysis.models import Userdbs

# import modules for processing data
from dateutil.parser import parse
import datetime #need to get today's date as the default
import json

# add path for analysis scripts
sys.path.append(os.path.join(os.getcwd(), "../analysis"))
sys.path.append(os.path.join(os.getcwd(), ".."))

# import analysis modules
import topsenders
import responseRateByTime
import topsent
from statsbyhour import *
from timeline import *
from contacts import Contacts
import getdata
import psycopg2
import sent_tab

#getdata.setup_db(conn)

class RefreshForm(forms.Form):

    def __init__(self, user, *args, **kwargs):
        super(RefreshForm, self).__init__(*args, **kwargs)
        self.fields['accounts'].queryset = user.account_set.all()
    
    accounts = forms.ModelChoiceField(queryset=[])
    password = forms.CharField(widget=forms.PasswordInput)


class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField()
    sender = forms.EmailField()
    recipients = forms.EmailField()
    cc_myself = forms.BooleanField(required=False)

class LoginForm(forms.Form):
#    username = forms.CharField(widget=forms.TextInput(attrs={'size':'25','style':'font-size:18px'}),max_length=100)
    username = forms.EmailField(widget=forms.TextInput(attrs={'size':'25','style':'font-size:18px'}), max_length=100)
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
    dictionary = {"url_count":"/emailanalysis/byhour/json/", "url_time":"/emailanalysis/byhour/json/", "url_rate":"/emailanalysis/getrate/json/", "isRecMail":"true", "topListURL":"/emailanalysis/topsenders/json/"}
    dictionary["top_email_title"] = "Top Email Responders"
    dictionary["top_email_desc"] = "Contacts who most frequently email you."
    dictionary["email_count"] = "Email Responses"
    dictionary["email_count_desc"] = "Number of emails you received."
    return render_to_response('emailanalysis/results.html',dictionary ,context_instance=RequestContext(request))

@login_required(login_url='/emailanalysis/login/')
def results_sent(request):
    dictionary = {"isRecMail":"false", "topListURL":"/emailanalysis/topsent/json/", "url_count":"/emailanalysis/countsent/json/", "url_rate":"/emailanalysis/rate_sent/json"}
    dictionary["top_email_title"] = "Top Email Contacts"
    dictionary["top_email_desc"] = "Contacts who you most frequently email."
    dictionary["email_count"] = "Sent Emails"
    dictionary["email_count_desc"] = "Number of emails you sent."
    return render_to_response('emailanalysis/results.html', dictionary, context_instance=RequestContext(request))

# login view
def login_view(request):
    
    if request.method == 'POST':
        form = LoginForm(request.POST)

        #check if the form is valid
        if form.is_valid():
            ##Check to make sure that the form has been filled out
            if (form.cleaned_data['username'] and form.cleaned_data['password']):
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']

                # check if gmail password is valid
                try:
                    getdata.authenticate_login('imap.googlemail.com',username,password)
                except:
                    # not valid --> need to find a better template to navigate to
                    return HttpResponse('user/password combo invalid')

                # check if user in db
                user = authenticate(username=username,password=password)
                if user is not None:
                    if user.is_active:
                        login(request,user)
                        # should redirect user to the results page
                        return HttpResponseRedirect("/emailanalysis/results/")
                    else:
                        return HttpResponse('user not recognized') # Return fail




                #############################
                #Need to add a method so that you can update the database with new 
                #messages. 
                #############################

                #if you don't have a user, then download data, return results page
                else:
                    user = User.objects.create_user(username,username,password)
                    user = authenticate(username=username,password=password)
                    login(request,user)
                    # create account for user
                    account = Account(user=user, host="imap.googlemail.com", username="username")
                    account.save()

                    #IMPORTANT: create the connection string and connect to the database
                    conn = connection
                    #conn_string = "host=localhost dbname=liamg user=liamg password=liamg"
                    #conn = psycopg2.connect(conn_string)
                    getdata.download_headers(account, password, conn, gettext=False)
                    
                    #make a connection and run the latencies script
                    c = conn.cursor()
                    
                    #get the account id for the specific user
                    actidSQL = "select id from accounts where user_id = (select id from auth_user where username = '%s');" % user
                    c.execute(actidSQL)
                    actid = c.fetchone()[0]
                    
                    #call refresh the latencies table
                    getdata.execute_latencies(actid, conn)

                    #redirect to results page
                    return HttpResponseRedirect("/emailanalysis/results")

        else:
            return HttpResponse('form invalid')
    else:

        form = LoginForm(initial={'username':'','password':'','defaultdb':False})
        c = {}
        c.update(csrf(request))

        return render_to_response('emailanalysis/home.html', {
            'form': form,
            },context_instance=RequestContext(request))

###################
#Is this method necessary?
#####################
# create new user
#def create_user(request):

#    if request.method == 'POST':
#        form = CreateUserForm(request.POST)
#        if form.is_valid():
#            username = form.cleaned_data['username']
#            email = form.cleaned_data['email']
#            password = form.cleaned_data['password']

            # create user
#            user = User.objects.create_user(username,email,password)

#            return HttpResponse('user created')
#        else:
#            return HttpResponse('form invalid')
#    else:
#        form = CreateUserForm()
#        c = {}
#        c.update(csrf(request))

#        return render_to_response('emailanalysis/newuser.html', {
#            'form': form,
#            },context_instance=RequestContext(request))
################    

# log out user
def logout_view(request):
    logout(request)

    form = LoginForm(initial={'username':'', 'password':'', 'defaultdb':False})
    c = {}
    c.update(csrf(request))
    return render_to_response('emailanalysis/home.html', {'form':form}, context_instance=RequestContext(request))

# get json data
@login_required(login_url='/emailanalysis/login/')
#@transaction.commit_manually
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
    

    curruser = User.objects.get(username=request.user)

    #ATTENTION: going to need to change the host once we deploy live
    #conn_string = "host=localhost dbname=liamg user=liamg password=liamg"

    #connect to db to get the data
    #conn = psycopg2.connect(conn_string)
    conn = connection


    #get the curruser id so that you can pass it to the functions below
    curridsql = "select id from accounts where user_id = %s"
    c = conn.cursor()
    c.execute(curridsql, (request.user.pk,))
    currid = c.fetchone()[0]

###################
#This portion of the code will be to retrieve the graph data for the rec'd tab
###################

    #get the top people who respond to the user
    if datatype == 'topsenders':
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get ('end', None)
        top = 10       
        email = curruser.username
        data = topsenders.get_top_senders(top, start, end, email, conn)

    #use this to get the mini graph next to the top ten that displays count
    elif datatype == "getcount":
        #called from timeline.py
        bd = ByDayNorm()
        queries = []
        
        #get the queries for the line charts in the top ten
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end, granularity=granularity, email=email, currid=currid)))
        ld = BDLineData()
        chartdata, maxval = ld.get_data(queries, conn, 1, granularity=granularity, start=start, end=end)
        data = [chartdata, maxval]

    #get the rate for a specifc user (filtered) and for the general population
    elif datatype == "getrate":
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get('end', None)
        emailAddy = curruser.username
        replyAddy = req.get('email', 'ALL')
        #if there is an empty email string, then set the replyAddy to ALL - this
        #will filter for the entire database
        if replyAddy == "":
            replyAddy = 'ALL'
        mode = req.get('mode', None)
        data = responseRateByTime.get_response_rate(mode, start, end, emailAddy, replyAddy, conn)

    #use this to get the count in the first graph for the rec'd tab
    elif datatype == "byhour":
        #called from statsbyhour.py
        ebh = RepliesByHour()
        queries = []
        queries.append(('y', ebh.get_sql(lat=lat, reply=reply, start=start, end=end,
                                         daysofweek=daysofweek, email=email, currid = currid)))
        ld = LineData()
        data = ld.get_data(queries, conn)
    
    #Update: WHAT DOES THIS DO?
#    elif datatype == "contacts":
#        contacts = Contacts()
#        data = contacts.get_data(conn)

    #Update: NOT SURE WHAT THIS DOES?
#    elif datatype == "getlatency":
#        bd = ByDay()
#        queries = []
#        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end,
#                                        granularity=granularity, email=email)))
#        ld = BDLineData()

#        chartdata, maxval = ld.get_data(queries, conn, 0, granularity=granularity, start=start, end=end)
#        data = [chartdata, maxval]

 
########################
#This portion of the code will be for the sent tab
########################

    #get the sent top ten people who the user contacts
    elif datatype == "topsent":
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get('end', None)
        top = 10 
        email = curruser.username
        data = topsent.get_top_sent(top, start, end, email, conn)

   #TODO: use this to get the mini charts for the sent tab
    elif datatype == "countmini":
        print 'hello' #enter code here
    
    #Use this to get the count of emails that a person sends to others
    elif datatype == "countsent":
        queries = []
        user = curruser.username
        
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get('end', None)
        to_email = req.get('email', None)
        queries.append(('y',sent_tab.get_count_sent_sql(start, end, user, to_email, conn)))
        ld = LineData()
        data = ld.get_data(queries, conn)

    #TODO: use this to get the delay between when user responds to emails that others send to them
    elif datatype == "delay_sent":
        print 'hello'#enter code here that gets the delay
    
    elif datatype == "rate_sent":
        #WIP: working on the connection to the already made algorithm for determining rate
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get('end', None)
        replyAddy = curruser.username
        emailAddy = req.get('email', 'ALL')
        #if there is an empty email string, then set the replyAddy to ALL - this
        #will filter for the entire database
        if emailAddy == "":
            emailAddy = 'ALL'
        mode = req.get('mode', None)
        data = responseRateByTime.get_response_rate(mode, start, end, emailAddy, replyAddy, conn)

    else:
        return HttpResponse('json call not recognized')

    # return data as json
    return HttpResponse(json.dumps(data), mimetype="application/json")


#UPDATE: Not all of this is being used. why do we have this method?
#@login_required
#def sendmail(request):

#    if request.method == 'POST':
#        form = ContactForm(request.POST)
#        if form.is_valid():
#            subject = form.cleaned_data['subject']
#            message = form.cleaned_data['message']
#            sender = form.cleaned_data['sender']
#            cc_myself = form.cleaned_data['cc_myself']

#            recipients = [form.cleaned_data['recipients']]
#            if cc_myself:
#                recipients.append(sender)



#            email = EmailMessage(subject, message, sender, recipients)
#            email.attach_file('images/Lydia.jpg')
#            email.send()
#            send_mail(subject, message, sender, recipients)
            #return HttpResponseRedirect('/thanks/') # Redirect after POST
        

    #send_mail('Welcome!','this is inbox doctor. i will tell you when you suck at responding to emails. inbox.dr was taken, so that\'s why it\'s inbox.doctor.', 'inbox.doctor@gmail.com', ['zhenya.gu@gmail.com','sirrice@gmail.com', 'ravdawg@gmail.com','farm.cp@gmail.com','melty710@gmail.com','jeezumpeez@gmail.com'], fail_silently=False)

#            return HttpResponse('mail sent')

#    else:
#        form = ContactForm()
#        c = {}
#        c.update(csrf(request))

#        return render_to_response('emailanalysis/sendmail.html', {
#            'form': form,
#            },context_instance=RequestContext(request))
#############
 

#####################
#Are these methods here for refreshing the data in the database?
#I don't think we are using them right now. Do we need to keep them around to use
#them in the future?
####################



@login_required
def refresh_account(request):
#going to call this view when we need to refresh the accounts with new data
    user = request.user
    if request.method == 'GET':
        form = RefreshForm(user)
        return render_to_response('emailanalysis/refresh_form.html',
                                  {'form' : form},
                                  context_instance = RequestContext(request))
    else:
        form = RefreshForm(user, request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            account = form.cleaned_data['accounts']
            
            running = account.check_for_new(password)
            return HttpResponseRedirect('/emailanalysis/refresh/wait/%d/' % account.pk)
    return render_to_response('emailanalysis/refresh_form.html',
                              {'form' : form},
                              context_instance = RequestContext(request))

@login_required
def refresh_wait(request, aid):
    account = Account.objects.get(pk=aid)
    return render_to_response('emailanalysis/refresh_wait.html',
                              {'account' : account},
                              context_instance = RequestContext(request))



@login_required
def refresh_check(request, aid):
    account = Account.objects.get(pk=aid)
    if not account or account.user != request.user:
        data = {'error' : True}
    else:
        data = {'error' : False,
                'done' : not account.refreshing,
                'max_dl_mid' : account.max_dl_mid,
                'max_mid' : account.max_mid,
                'last_refresh' : str(account.last_refresh)}
    return HttpResponse(json.dumps(data), mimetype="application/json")    
        
        
    
