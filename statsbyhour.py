from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import numpy as np
import sys


class StatsByHour(object):
    ME_REPLY = """select avg(lat) as avglat, strftime('%%H', sentdate) as hour,
    CAST(strftime('%%M', sentdate)/60 as integer) as minute
    from latency l, contacts me
    where strftime('%%Y', sentdate) >= 2010 and me.name like '%%%s%%' and
    me.id = l.replyuid and l.lat < 1 %s
    group by hour, minute
    order by hour, minute asc;"""

    ME_SEND = """select avg(lat) as avglat, strftime('%%H', sentdate) as hour,
    CAST(strftime('%%M', sentdate)/60 as integer) as minute
    from latency l, contacts me
    where strftime('%%Y', sentdate) >= 2010 and me.name like '%%%s%%' and
    me.id = l.senduid and l.lat < 1 %s
    group by hour, minute
    order by hour, minute asc;"""

    REPLY_COUNT = """select count(*), strftime('%%H', sentdate) as hour,
    CAST(strftime('%%M', sentdate)/60 as integer) as minute
    from latency l, contacts me
    where strftime('%%Y', sentdate) >= 2010 and me.name like '%%%s%%' and
    me.id = l.replyuid and l.lat < 1 %s
    group by hour, minute
    order by hour, minute asc;"""


    SEND_COUNT = """select count(*), strftime('%%H', sentdate) as hour,
    CAST(strftime('%%M', sentdate)/60 as integer) as minute
    from latency l, contacts me
    where strftime('%%Y', sentdate) >= 2010 and me.name like '%%%s%%' and
    me.id = l.senduid and l.lat < 1 %s
    group by hour, minute
    order by hour, minute asc;"""


    def sql_date_range(self, start, end, name="eugene"):
        date_range = "and datetime(sentdate) > datetime('%s') and datetime(sentdate) < datetime('%s')" % (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d') )

        reply = self.REPLY_COUNT % (name, date_range)
        send = self.SEND_COUNT % (name, date_range)
        return reply, send

    def sql_weekend(self, start=None, end=None, name="eugene"):
        weekend = "and (strftime('%w', sentdate) = '6' or strftime('%w', sentdate) = '0')"
        if start and end:
            date_range = "and datetime(sentdate) > datetime('%s') and datetime(sentdate) < datetime('%s')" % (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d') )
            WHERE = "%s %s" % (date_range, weekend)
        reply = self.REPLY_COUNT % (name, WHERE)
        send = self.SEND_COUNT % (name, WHERE)
        return reply, send

    def sql_weekday(self, start=None, end=None, name="eugene"):
        weekend = "and not (strftime('%w', sentdate) = '6' or strftime('%w', sentdate) = '0')"
        if start and end:
            date_range = "and datetime(sentdate) > datetime('%s') and datetime(sentdate) < datetime('%s')" % (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d') )
            WHERE = "%s %s" % (date_range, weekend)
        reply = self.REPLY_COUNT % (name, WHERE)
        send = self.SEND_COUNT % (name, WHERE)
        return reply, send


    def proc_rows(self, res):
        return map(lambda row: map(float, row), res)

    def get_data(self):
        conn = sqlite3.connect('./mail.db', detect_types=sqlite3.PARSE_DECLTYPES)

        #to_x = lambda 
        cur = conn.cursor()

        colors = ['r-', 'b-', 'o-', 'y-', 'g-']
        queries = []
        queries.append(("2011", self.sql_date_range(date(2011, 1, 1), date.today())))
        queries.append(("2010", self.sql_date_range(date(2010, 1, 1), date(2011, 1, 1))))
        queries.append(("Spring 2010", self.sql_date_range(date(2010, 1, 1), date(2010, 4, 1))))
        queries.append(("Summer 2010", self.sql_date_range(date(2010, 4, 1), date(2010, 7, 1))))
        queries.append(("Fall 2010", self.sql_date_range(date(2010, 7, 1), date(2010, 10, 1))))
        queries.append(("Winter 2010", self.sql_date_range(date(2010, 10, 1), date(2010, 11, 1))))
        queries.append(("Weekend 2011", self.sql_weekend(date(2011, 1, 1), date.today())))
        queries.append(("Weekday 2011", self.sql_weekday(date(2011, 1, 1), date.today())))
        queries.append(("Weekend 2010", self.sql_weekend(date(2010, 1, 1), date(2011, 1, 1))))
        queries.append(("Weekday 2010", self.sql_weekday(date(2010, 1, 1), date(2011, 1, 1))))

        data = {}
        labels = []

        i = 0
        #while i < 100:
        #title, sqls = queries[i % len(queries)]
        for title, sqls in queries:
            i += 1
            #plt.cla()        
            #plt.clf()
            for idx, sql in enumerate(sqls):
                res = cur.execute(sql)
                res = self.proc_rows(res)
                avgs = [row[0] for row in res]            
                xs = [datetime(2000, 1, 1, int(row[1]), int(row[2] * 60)) for row in res]

                if idx == 0:
                    data["My replies: %s" % title] = avgs
                else:
                    data["Reply to me: %s" % title] = avgs

                #plt.plot(xs, avgs, colors[idx])
                #plt.show()
                #plt.draw()
                if not labels :
                    labels = map(str, xs)



                #if 'x' in sys.stdin.readline():
                #break

        cur.close()
        data['labels'] = labels
        return data
        


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    plt.ion()


    stats = StatsByHour()
    data = stats.get_data()
    import json
    print json.dumps(data)
        
        

