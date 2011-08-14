from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import sys



class BDLineData(object):

    def proc_rows(self, res):
        return map(tuple, map(lambda row: [float(row[0]), int(row[1]), parse(row[2])], res))

    def get_data(self, queries, statid=0, granularity=None):
        conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)

        cur = conn.cursor()
        tmpdata = {}
        labels = []
        start = None
        end = None

        i = 0
        for title, sql in queries:
            res = cur.execute(sql)
            res = self.proc_rows(res)
            d = {}
            for lat, count, date in res:
                d[date] = (lat, count)
                if not start or date < start: start = date
                if not end or date > end: end = date
            tmpdata[title] = d

        td = granularity == 'week' and timedelta(days=7) or timedelta(days=1)
        xs = []
        while start <= end:
            xs.append(start)
            start += td

        data = {}
        for title, d in tmpdata.items():
            data[title] = [x in d and d[x][statid] or 0 for x in xs]

        cur.close()

        
        data['labels'] = map(lambda d: d.strftime('%Y-%m-%d'), xs)
        return data



class ByDay(object):
    def get_sql(self, lat=True, reply=True, start=None, end = None,
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
    bd = ByDay()
    queries = []
    queries.append(('lydia', bd.get_sql(name="zheny")))
    ld = BDLineData()
    data = ld.get_data(queries)
    import json
    print json.dumps(data)
