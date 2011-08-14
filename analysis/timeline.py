from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import sys



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
            res = cur.execute(sql)
            res = self.proc_rows(res)
            d = {}
            for lat, count, date in res:
                d[date.strftime('%Y-%m-%d')] = (lat, count)
                if not start or date < start: start = date
                if not end or date > end: end = date
                maxs[0] = max(maxs[0], lat)
                maxs[1] = max(maxs[1], count)
            tmpdata[title] = d

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
        for title, d in tmpdata.items():
            data[title] = [x in d and d[x][statid] or 0 for x in xs]
            data[title][-1] = maxs[statid]
        data['labels'] = xs        

        cur.close()

        print "array lengths", start, end, map(len, data.values())
        return data


class ByDayNorm(object):
    def get_sql(self, lat=True, reply=None, start=None, end = None,
                granularity=None, email=None):
        
        WHERE = []
        if start:
            WHERE.append("datetime(date) > datetime('%s')" % start.strftime('%Y-%m-%d'))
        if end:
            WHERE.append("datetime(date) < datetime('%s')" % end.strftime('%Y-%m-%d'))

        WHERE.append("(me.id = m.fr)")

        if email:
            WHERE.append("me.email like '%%%s%%'" % email)

        if granularity == 'week':
            SELECT = "count(*), count(*), date(date, '-'||strftime('%w',date)||' days') as date"
        else:
            SELECT = "count(*), count(*), date(date) as date"

        WHERE = ' and '.join(WHERE)

        sql = "SELECT %s FROM msgs m, contacts me WHERE %s GROUP BY date ORDER BY date asc;" % (SELECT, WHERE)
        return sql





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
