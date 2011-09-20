#####################
#This tab will contain all the methods necessary to return the data for the sent tab
#except for the topsent users. It will contain:
#countmini - shows the mini count for each of the topsent emails
#countsent - shows the number of emails that the user sends over the day
#delay_sent - shows the delay between how the user responds to incoming mails
#rate_sent - leverages the responseRate.py to get the rate the user responds to mail
####################

import sys
import datetime
import psycopg2
import re
import json
import math

def get_count_sent_sql(start, end, user, to_email, conn):
    #query to get the number of sent emails for a specific user
    print 'entered get_count_sent'
    c = conn.cursor()
    if to_email != None:
        #use the specfic email

        sql = """select count(*), extract('hour' from emails.date) as hour
                   from tos, emails
                   where email_id = emails.id and emails.account = 
                     (select id from accounts where user_id =
                        (select id from auth_user where username = '%s'))
                   and emails.date >= '%s' and emails.date < '%s'
                 group by hour
                 order by hour asc""" % (user, start, end)
    else:
        sql = """select count(*), extract('hour' from emails.date) as hour 
                   from tos, emails 
                   where email_id = emails.id and emails.account = 
                      (select id from accounts where user_id = 
                         (select id from auth_user where username = '%s')) 
                   and emails.date >= '%s' and emails.date < '%s'
                 group by hour 
                 order by hour asc;""" % (user, start, end)
    print sql 
    return sql
