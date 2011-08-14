from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import sys


class Contacts(object):
    def get_data(self):
        conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)

        cur = conn.cursor()
        res = cur.execute("select email, count(*) as count from msgs, contacts where contacts.id = msgs.fr group by email having count(*) > 5 order by count desc")
        emails = []
        for row in res:
            emails.append(row[0])

        cur.close()
        return emails
