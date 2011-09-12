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
    dictionary = {"url_count":"/emailanalysis/byhour/json/", "url_time":"/emailanalysis/byhour/json/", "url_rate":"/emailanalysis/getrate/json/", "isRecMail":"true", "topListURL":"/emailanalysis/topsenders/json/"}
    dictionary["top_email_title"] = "Top Email Responders"
    dictionary["top_email_desc"] = "Contacts who most frequently email you."
    dictionary["email_count"] = "Email Responses"
    dictionary["email_count_desc"] = "Number of emails you received."
    return render_to_response('emailanalysis/results.html',dictionary ,context_instance=RequestContext(request))

@login_required(login_url='/emailanalysis/login/')
def results_sent(request):
    dictionary = {"isRecMail":"false", "topListURL":"/emailanalysis/topsent/json/"}
    dictionary["top_email_title"] = "Top Email Contacts"
    dictionary["top_email_desc"] = "Contacts who you most frequently email."
    dictionary["email_count"] = "Sent Emails"
    dictionary["email_count_desc"] = "Number of emails you sent."
    return render_to_response('emailanalysis/results.html', dictionary, context_instance=RequestContext(request))

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
                # user doesn't exist: create user
                # download data, return results page
                else:
                    user = User.objects.create_user(username,username,password)
                    user = authenticate(username=username,password=password)
                    login(request,user)
                    # create account for user
                    account = Account(user=user, host="imap.googlemail.com", username="username")
                    account.save()

                    # # create database name for user
                    # userdb = Userdbs(username=username)
                    # userdb.save() # creates userdb.id
                    # dbname = 'user{0}.db'.format(userdb.id)
                    # userdb.dbname = dbname
                    # userdb.save()

                    # conn = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES)

                    # #need to find a way to make one database
                    # getdata.setup_db(conn)
                    # getdata.download_headers('imap.googlemail.com',username,password,conn)
                    # os.system('./analyzedb.sh {0}'.format(dbname))
                    # conn.close()

                    #IMPORTANT: create the connection string and connect to the database
                    conn_string = "host=localhost dbname=liamg user=liamg password=liamg"
                    conn = psycopg2.connect(conn_string)
                    getdata.download_headers(account, password, conn, gettext=False)
                    
                    #make a connection and run the latencies script
                    c = conn.cursor()
                    
                    #get the account id for the specific user
                    actidSQL = "select id from accounts where user_id = (select id from auth_user where username = '%s');" % user
                    c.execute(actidSQL)
                    actid = c.fetchone()[0]
                    print actid
                    
                    #fill the latencies table
                    latencies_sql = """INSERT into latencies
                    (account, replier, sender, replyemail, origemail, replydate, origdate, lat)
                    SELECT m1.account, c1.id as replier, c2.id as sender,
                           m1.id AS replyemail, m2.id AS origemail,
                           m1.date AS replydate, m2.date AS origdate,
                           (extract (epoch from m1.date::timestamp) - extract(epoch from m2.date::timestamp)) AS lat
                    FROM contacts c1, contacts c2, emails m1, emails m2
                    WHERE m1.id > m2.id AND m1.reply = m2.mid AND
                          c1.id = m1.fr AND c2.id = m2.fr AND m1.account = %s AND
                          m1.account = m2.account;""" % (actid)


                    #commit the data
                    c.execute(latencies_sql)
                    conn.commit()


                    #redirect to results page
                    return HttpResponseRedirect("/emailanalysis/results")

        else:
            return HttpResponse('form invalid')
    else:
#        form = LoginForm(initial={'username':'default@default.com','password':'default','defaultdb':True})
        form = LoginForm(initial={'username':'','password':'','defaultdb':False})
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
#    return HttpResponse('user logged out')
    form = LoginForm(initial={'username':'', 'password':'', 'defaultdb':False})
    c = {}
    c.update(csrf(request))
    return render_to_response('emailanalysis/home.html', {'form':form}, context_instance=RequestContext(request))

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
    

    curruser = User.objects.get(username=request.user)

    #ATTENTION: going to need to change the host once we deploy live
    conn_string = "host=localhost dbname=liamg user=liamg password=liamg"

    #connect to db to get the data
    conn = psycopg2.connect(conn_string)

    #DEPRECATED: for the sqlite prototype database
    #conn = sqlite3.connect(curruser.dbname, detect_types=sqlite3.PARSE_DECLTYPES)


    #get the curruser id so that you can pass it to the functions below
    curridsql = "select id from accounts where user_id = (select id from auth_user where username = '%s')" % curruser
    c = conn.cursor()
    c.execute(curridsql)
    currid = c.fetchone()[0]



    #get the top people who respond to the user
    if datatype == 'topsenders':
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get ('end', None)
        top = 10       
        email = curruser.username
        data = topsenders.get_top_senders(top, start, end, email, conn)
    
    #get the sent top ten people who the user contacts
    elif datatype == "topsent":
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get('end', None)
        top = 10 
        email = curruser.username
        data = topsent.get_top_sent(top, start, end, email, conn)

    #get the rate for a specifc user (filtered) and for the general population
    elif datatype == "getrate":
        req = request.REQUEST
        start = req.get('start', None)
        end = req.get('end', None)
        emailAddy = curruser.username
        replyAddy = req.get('email', None)
        mode = req.get('mode', None)
        data = responseRateByTime.get_response_rate(mode, start, end, emailAddy, replyAddy, conn)

    #use this to get the count in the first graph and maybe the second graph?
    elif datatype == "byhour":
        ebh = RepliesByHour()
        queries = []
        print "EMAIL", email

        queries.append(('y', ebh.get_sql(lat=lat, reply=reply, start=start, end=end,
                                         daysofweek=daysofweek, email=email, currid = currid)))
        ld = LineData()
        data = ld.get_data(queries, conn)

    #not sure what this does yet?
    elif datatype == "contacts":
        contacts = Contacts()
        data = contacts.get_data(conn)

    #get the second graph that shows the response time
    elif datatype == "getlatency":
        bd = ByDay()
        queries = []
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end,
                                        granularity=granularity, email=email)))
        ld = BDLineData()

        data = ld.get_data(queries, conn, 0, granularity=granularity, start=start, end=end)


    #use this to get the small graph next to the top ten
    elif datatype == "getcount":
        bd = ByDayNorm()
        queries = []

        #get the queries for the line charts in the top ten
        queries.append(('y', bd.get_sql(lat=lat, reply=reply, start=start, end=end, granularity=granularity, email=email, currid=currid)))
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


@login_required
def refresh_account(request):
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
        
        
    
