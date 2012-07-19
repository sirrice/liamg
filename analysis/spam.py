
#Draft of the top people the user sends emails to - need to double check the sql command

import sys, random, smtplib, time, urllib
import sqlite3, email, imaplib, math
from dateutil.parser import parse
from datetime import timedelta
from optparse import OptionParser
import re

def get_spam_contacts(account_id, conn):
    try:
        c = conn.cursor()
#        sql = """select contacts.id
#        from contacts
#        where owner_id = %s and
#              not exists (select * from tos where tos.contact_id = contacts.id) and
#              not exists (select * from ccs where ccs.contact_id = contacts.id) and
#              not exists (select * from bccs where bccs.contact_id = contacts.id);"""
        sql = """select contacts.id
                 from contacts
                 where owner_id = %s and contacts.name is not null"""
        c.execute(sql, (account_id,))
        res = c.fetchall()

        return map(int, res)
    except Exception, e:
        print >>sys.stderr, e
        return []
              
def get_non_spam_contacts(start, end, user, conn):
    c = conn.cursor()
    try:
        dateStr = " date >= '" + start + "' and date < '"+  end + "'" 
        sql = """select email, count(*) as c from contacts inner join 
                  (select contact_id, date, subj from 
                     (select id, date, subj from emails where fr = 
                        (select id from contacts where email = '%s' and owner_id = 
                           (select id from auth_user where email = '%s'))
                     and %s) 
                  as msgids inner join tos on tos.email_id = msgids.id) 
               as cids on contacts.id = cids.contact_id 
               group by email 
               order by c desc;""" % (user, user, dateStr)

        c.execute(sql)
        res = c.fetchall()
        
        emails = []
        for item in res:
            emails.append(item[0])

        return emails
    except Exception, e:
        print e
        print "exception in get emails topsent"
