import topsent
from optparse import OptionParser
import random, smtplib, sys, time, urllib
import sqlite3, email, math, imaplib
from dateutil.parser import parse
from datetime import timedelta
import json
import psycopg2
import re


def get_top_senders(num, startdate, enddate, user, conn):
    c = conn.cursor()
    try:
        num = num+1
        
        #might need a better way to do this -- if we have a business account there will be other email strings that we can't account for. However if we include
        #everything then we will not be able to filter out the spam that people send to the user
        #email_list = ["'%yahoo%'", "'%gmail%'", "'%aol%'", "'%hotmail%'", "'%live.com%'"]
        #for now going to use the senders list to predict who is important -> a person wouldn't send an email unless they were on the senders list

        email_list = topsent.get_emails_topsent(startdate, enddate, user, conn)      
        email_list = ["'%{0}%'".format(email) for email in email_list]

        emailStr = "and (email like " + " or email like ".join(email_list) + ")"
        dateStr = "and date >= '" + startdate + "' and date < '" + enddate + "'"

        execCode = 'select email, count(*) as c from emails, contacts where emails.fr = contacts.id %s %s group by email order by c desc limit %d;' % (emailStr, dateStr, num)

        c.execute(execCode)
        res = c.fetchall()
    except Exception, e:
        print 'theres an error. we are in the catch block.'
        print >> sys.stderr, e
        print e
        res = None
    total = 0
    emails = []
    numbers = []
    for item in res:
        total += int(item[1])
        emails.append(item[0])
        numbers.append(item[1])

    #get rid of the current user in the lists
    if user in emails:
        index = emails.index(user)
        emails.remove(user)
        numbers.remove(numbers[index])

    obj = dict()
    obj["labels"] = emails 
    obj["y"] = numbers
    

    return obj



if __name__ == "__main__":
    inputarg = 10
    if len(sys.argv) == 4:
        inputarg = sys.argv[1]
        start = sys.argv[2]
        end = sys.argv[3]
    else:
        sys.stderr.write("Not valid argmuents")
        exit(1)

    conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    get_top_senders(10, start, end, conn)

#obj = dict()

#myemails, mynumbers = get_top_senders(int(inputarg))

#obj["x"] = myemails
#obj["y"] = mynumbers

#print json.dumps(obj)


