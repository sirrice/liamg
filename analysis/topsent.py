#Draft of the top people the user sends emails to - need to double check the sql command

import sys, random, smtplib, time, urllib
import sqlite3, email, imaplib, math
from dateutil.parser import parse
from datetime import timedelta
from optparse import OptionParser
import re

def get_top_sent(num, start, end, user, conn):
    """
    num: the limit clause
    start: start date
    end: end date
    user: complete username
    """
    c = conn.cursor()
    if True:#try:
        #identify the user that we want to get the emails for
        num = num + 1

        #get the user login ID
      #  c.execute("select accounts.id from accounts, auth_user as au where au.username = %s and au.id = accounts.user_id", (user,))
      #  aid = c.fetchone()[0]

        #get the user contact ID
      #  c.execute("select id from contacts where email = %s", (user,))
      #  my_cid = c.fetchone()[0]


      #  WHERE = []
      #  WHERE.append("date >= %s and date < %s")
      #  WHERE.append("emails.account = %s")
      #  WHERE.append("emails.fr = %s")
      #  WHERE.append("tos.email_id = emails.id")
      #  WHERE.append("contacts.id = tos.contact_id")
      #  WHERE = ' and '.join(WHERE)

        #        sqlCmd = "select email, count(*) as c from contacts inner join (select contact_id, date, subj from (select id, date, subj from emails where fr = (select id from contacts where email = '%s' and owner_id = (select id from auth_user where email = '%s')) and %s) as msgids inner join tos on tos.email_id = msgids.id) as cids on contacts.id = cids.contact_id group by email order by c desc limit %d;" % (user, user, dateStr, num)

       # sql = """select contacts.email, count(*) as c
       # from contacts, emails, tos
       # where %s
       # group by contacts.email
       # order by c desc
       # limit %s;""" % (WHERE, num)

        #replacing current SQL query for now
        dateStr = "date >= '%s' and date < '%s'" % (start, end)
        sql = "select email, count(*) as c from contacts inner join (select contact_id, date, subj from (select id, date, subj from emails where fr = (select id from contacts where email = '%s' and owner_id = (select id from auth_user where email = '%s')) and %s) as msgids inner join tos on tos.email_id = msgids.id) as cids on contacts.id = cids.contact_id group by email order by c desc limit %d;" % (user, user, dateStr, num)
        
        print sql

       # c.execute(sql, (start, end, aid, my_cid))
        c.execute(sql)
        res = c.fetchall()
        
        emails = []
        number = []
        #push the emails into an array and count the total
        for item in res:
            emails.append(item[0])
            number.append(item[1])
        
        if user in emails:
            index = emails.index(user)
            emails.remove(user)
            number.remove(number[index])

        dictionary = dict()
        dictionary["labels"] = emails
        dictionary["y"] = number
        return dictionary

        
    # except Exception, e:
    #     print e
    #     print "error in connection"


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
    get_top_sent(num, start, end, 'sirrice@gmail.com', conn)


