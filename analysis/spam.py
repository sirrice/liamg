
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
        sql = """select contacts.id
        from contacts
        where owner_id = %s and
              not exists (select * from tos where tos.contact_id = contacts.id) and
              not exists (select * from ccs where ccs.contact_id = contacts.id) and
              not exists (select * from bccs where bccs.contact_id = contacts.id);"""

        c.execute(sql, (aid,))
        res = c.fetchall()
        return map(int, res)
    except Exception, e:
        print >>sys.stderr, e
        return []
              
