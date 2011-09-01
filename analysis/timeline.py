from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import sys
import psycopg2


class BDLineData(object):

    def proc_rows(self, res):
        return map(tuple, map(lambda row: [float(row[0]), int(row[1]), parse(row[2])], res))

    def get_data(self, queries, conn, statid=0, granularity=None, start=None, end=None):

        cur = conn.cursor()
        tmpdata = {}
        labels = []
        maxs = [0,0]

        i = 0

        for title, sql in queries:
            cur.execute(sql)
            res = cur.fetchall()
           # res = self.proc_rows(res)

            d = {}

            for lat, count, date in res:
                d[date.strftime('%Y-%m-%d')] = (lat, count)

                if not start or date < start: start = date
                if not end or date > end: end = date
                maxs[0] = max(maxs[0], lat)
                maxs[1] = max(maxs[1], count)
            tmpdata[title] = d
        #this is the tmp data that shows the counts for the specific times {'y': {'2010-01-01':(15, 15)}} - this is a dictionary
        print tmpdata
        if start == None:
            return {'labels' : [], 'y' : []}

        if granularity == "week":
            start = start - timedelta(days = ((start.weekday()+1)%7))
            end = end - timedelta(days = ((end.weekday()+1)%7))
            td = timedelta(days=7)
        else:
            td = timedelta(days=1)

        xs = []
        while start <= end:
            xs.append(start.strftime('%Y-%m-%d'))
            start += td

        data = {}
        print xs
        
        for title, d in tmpdata.items():
            print 'title and value', title, d
            data[title] = [x in d and d[x][statid] or 0 for x in xs]
            data[title][-1] = maxs[statid]
        data['labels'] = xs        

        cur.close()

        print "array lengths", start, end, map(len, data.values())

        return data


class ByDayNorm(object):
    def get_sql(self, lat=True, reply=None, start=None, end = None,
                granularity=None, email=None):
        try:

            WHERE = []
            
            if start:
                WHERE.append("date > '%s'" % start.strftime('%Y-%m-%d'))
            if end:
                WHERE.append("date < '%s'" % end.strftime('%Y-%m-%d'))

            if email:
                WHERE.append("m.fr = me.id and me.email like '%%%s%%' " % email)

            if granularity == 'week':
                SELECT = "count(*), count(*), cast(date as date) - cast(extract(week from date)||'weeks' as interval) as d from emails as m, contacts as me"
            else:
                SELECT = "count(*), count(*), date(date) as date"

            WHERE = ' and '.join(WHERE)

            sql = "SELECT %s WHERE %s GROUP BY d ORDER BY d asc;" % (SELECT, WHERE)
#            sql = "select count(*), count(*), cast(date as date) - cast(extract(week from date) || 'weeks' as interval) as d from emails as m, contacts as me where m.fr = me.id and me.email like '%gmail.com%' and date > '2010-08-25' and date < '2011-08-25' group by d order by d asc;"
            
            print sql
            return sql

        except Exception, e:
            print e
            print 'except in get_sql'




class ByDay(object):
    def get_sql(self, lat=True, reply=None, start=None, end = None,
                granularity=None, email="sirrice"):
        
        WHERE = []
        WHERE.append("l.lat < 1")
        if start:
            WHERE.append("datetime(sentdate) > datetime('%s')" % start.strftime('%Y-%m-%d'))
        if end:
            WHERE.append("datetime(sentdate) < datetime('%s')" % end.strftime('%Y-%m-%d'))

        if reply is None:
            WHERE.append("(me.id = l.replyuid or me.id = l.senduid)")
        elif reply:
            WHERE.append("me.id = l.replyuid")
        else:
            WHERE.append("me.id = l.senduid")
        if email:
            WHERE.append("me.email like '%%%s%%'" % email)

        if granularity == 'week':
            SELECT = "avg(lat), count(*), date(sentdate, '-'||strftime('%w',sentdate)||' days') as date"
        else:
            SELECT = "avg(lat), count(*), date(sentdate) as date"

        WHERE = ' and '.join(WHERE)

        sql = "SELECT %s FROM latency l, contacts me WHERE %s GROUP BY date ORDER BY date asc;" % (SELECT, WHERE)
        return sql


if __name__ == '__main__':
    conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    bd = ByDayNorm()
    queries = []
    queries.append(('lydia', bd.get_sql(email="zheny")))
    ld = BDLineData()
    data = ld.get_data(queries, conn)
    import json
    print json.dumps(data)
