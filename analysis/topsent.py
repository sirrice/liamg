#Draft of the top people the user sends emails to - need to double check the sql command

import sys, random, smtplib, time, urllib
import sqlite3, email, imaplib, math
from dateutil.parser import parse
from datetime import timedelta
from optparse import OptionParser
import re

def get_top_sent(num, start, end, user_sent_to, conn):
    c = conn.cursor()
    try:
        #identify the user that we want to get the emails for
        user = 'sirrice@gmail.com'
        dateStr = " date >= '" + start + "' and date < '"+  end + "'"
        #SQL command to group by email
        sqlCmd = "select email,count(*) as c from contacts inner join (select cid,date,subj from (select id,date,subj from msgs where fr = (select id from contacts where email = '" + user +"') and" + dateStr +") as 'msgids' inner join tos on tos.msg = msgids.id) as 'cids' on contacts.id = cids.cid group by email order by c desc limit " + num + ";"
        print sqlCmd

        res = c.execute(sqlCmd)
        res = res.fetchall()
        
        total_emails_sent = 0
        emails = []
        number = []
        #push the emails into an array and count the total
        for item in res:
            total_emails_sent +=1
            emails.append(item[0])
            number.append(item[1])
            
        print emails
        print number

    except:
        print "error in connection"

def get_total_for_user(emails, user_sent_to):
    total_sent_to_user = 0
    for item in emails:
        if item == user_sent_to:
            total_sent_to_user += 1
        
    return total_sent_to_user

if __name__ == "__main__":
    if len(sys.argv) == 5:
        num = sys.argv[1]
        start = sys.argv[2]
        end = sys.argv[3]
        user_sent_to = sys.argv[4]
    else:
        sys.stderr.write("not valid arguments")
        exit(1)

    conn = sqlite3.connect('../mail.db', detect_types = sqlite3.PARSE_DECLTYPES)  
    get_top_sent(num, start, end, user_sent_to, conn)


