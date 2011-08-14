
from optparse import OptionParser
import random, smtplib, sys, time, urllib
import sqlite3, email, math, imaplib
from dateutil.parser import parse
from datetime import timedelta
import json

import re


def get_top_senders(num, startdate, enddate, conn):

    c = conn.cursor()
    try:
        email_list = ["'%yahoo%'", "'%gmail%'", "'%aol%'", "'%hotmail%'", "'%live.com%'"]
        emailStr = "and (email like " + " or email like ".join(email_list) + ")"
        dateStr = "and date >= '" + startdate + "' and date < '" + enddate + "'"
        execCode = 'select email, count(*) as c from msgs, contacts where msgs.fr = contacts.id %s %s group by email order by c desc limit %d;' % (emailStr, dateStr, num)
        res = c.execute(execCode)
        res.fetchone()
        res = res.fetchall()
    except Exception, e:
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
    for item in res:
        length = float(item[1]) / float(total) * 100

        print "%35s %9s %s" % (item[0], item[1], "*"*int(length))
   
    obj = dict()
    obj["labels"] = emails 
    obj["y"] = numbers
    

    print obj
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


