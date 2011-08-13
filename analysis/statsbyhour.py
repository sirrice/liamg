from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import numpy as np
import sys




class LineData(object):

    def proc_rows(self, res):
        return map(tuple, map(lambda row: map(float, row), res))

    def get_data(self, queries):
        conn = sqlite3.connect('./mail.db', detect_types=sqlite3.PARSE_DECLTYPES)

        cur = conn.cursor()

        colors = ['r-', 'b-', 'o-', 'y-', 'g-']

        data = {}
        labels = []

        i = 0
        for title, sql in queries:

            res = cur.execute(sql)
            res = self.proc_rows(res)

            vals = []
            d = {}
            for val, hour in res:
                d[hour] = val
            for hour in xrange(24):
                if hour in d:
                    vals.append(d[hour])
                else:
                    vals.append(0)
                
            xs = [datetime(2000, 1, 1, hour) for hour in xrange(24)]
            data[title] = vals

            if not labels :
                labels = map(str, xs)

        cur.close()
        data['labels'] = labels
        return data

    def viz(self, data):
        xs = data['labels']

        maxy = max([max(avgs) for name, avgs in data.items() if name != 'labels'])
        for name, avgs in data.items():
            if name == 'labels': continue
            print name
            plt.cla()        
            plt.clf()
            xs = [x for x in xrange(len(xs))]

            plt.bar(xs, avgs, width=1)#colors[0])
            plt.ylim(0, int(maxy * 1.2))#max(50, max(avgs) + 10))
            plt.show()
            plt.draw()
            if 'x' in sys.stdin.readline():
                break
            


class RepliesByHour(LineData):
    def get_sql(self, lat=True, reply=True, start=None, end = None, daysofweek = None, name="eugene"):
        WHERE = []
        WHERE.append("l.lat < 1")
        if start:
            WHERE.append("datetime(sentdate) > datetime('%s')" % start.strftime('%Y-%m-%d'))
        if end:
            WHERE.append("datetime(sentdate) < datetime('%s')" % end.strftime('%Y-%m-%d'))
        if daysofweek:
            WHERE.append("strftime('%w', sentdate) in []" % (map(lambda x: "'%s'" % x, daysofweek)))
        if reply is None:
            WHERE.append("(me.id = l.replyuid or me.id = l.senduid)")
        elif reply:
            WHERE.append("me.id = l.replyuid")
        else:
            WHERE.append("me.id = l.senduid")
        if name:
            WHERE.append("me.name like '%%%s%%'" % name)

        if lat:
            SELECT = "avg(lat) as avglat, strftime('%H', sentdate) as hour" # , CAST(strftime('%M', sentdate)/60 as integer) as minute"
        else:
            SELECT = "count(*), strftime('%H', sentdate) as hour"#, CAST(strftime('%M', sentdate)/60 as integer) as minute"

        WHERE = ' and '.join(WHERE)

        sql = "SELECT %s FROM latency l, contacts me WHERE %s GROUP BY hour ORDER BY hour asc;" % (SELECT, WHERE)
        return sql


class AllByHour(LineData):
    def get_sql(self, lat=True, start=None, end = None, daysofweek = None, name="eugene"):
        WHERE = []
        WHERE.append("l.lat < 1")
        if start:
            WHERE.append("datetime(sentdate) > datetime('%s')" % start.strftime('%Y-%m-%d'))
        if end:
            WHERE.append("datetime(sentdate) < datetime('%s')" % end.strftime('%Y-%m-%d'))
        if daysofweek:
            WHERE.append("strftime('%w', sentdate) in []" % (map(lambda x: "'%s'" % x, daysofweek)))

        if lat:
            SELECT = "avg(lat) as avglat, strftime('%H', sentdate) as hour"#, CAST(strftime('%M', sentdate)/60 as integer) as minute"
        else:
            SELECT = "count(*), strftime('%H', sentdate) as hour"#, CAST(strftime('%M', sentdate)/60 as integer) as minute"

        WHERE = ' and '.join(WHERE)

        sql = "SELECT %s FROM latency l WHERE %s GROUP BY hour ORDER BY hour asc;" % (SELECT, WHERE)
        return sql
    


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import json
    plt.ion()

    stats = AllByHour()
    queries = []

    for month in xrange(12):
        month += 1
        start = date(2010, month, 1)
        end = start + timedelta(days=30)
        #queries.append(('Count 2011 %d' % month, stats.get_sql(lat=False, reply=None, start=start, end = end)))
        queries.append(('Count 2011 %d' % month, stats.get_sql(lat=True, start=start, end = end)))
    data = stats.get_data(queries)
    stats.viz(data)

    print json.dumps(data)
        
        

