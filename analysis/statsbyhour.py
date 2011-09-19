from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import sqlite3, math
import sys



class LineData(object):

    def proc_rows(self, res):
        return map(tuple, map(lambda row: map(float, row), res))

    def get_data(self, queries, conn):
        
        #get the data. connect to the database and create the labels for the x and y axis
        cur = conn.cursor()

        colors = ['r-', 'b-', 'o-', 'y-', 'g-']

        data = {}
        labels = []

        i = 0
        for title, sql in queries:
            print sql
            cur.execute(sql)

            res = cur.fetchall()
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
                
            xs = [self.itos(hour) for hour in xrange(24)]
            data[title] = vals

            if not labels :
                labels = map(str, xs)

        cur.close()
        data['labels'] = labels
        return data

    def itos(self, hour):
        if hour == 0:
            label = "Midnight"
        elif hour< 12:
            label = "%s AM" % hour
        elif hour == 12:
            label = "Noon"
        else:
            label = "%d PM" % (hour - 12)
        return label
        

    def viz(self, data):
        xs = data['labels']

        maxy = max([max(avgs) for name, avgs in data.items() if name != 'labels'])
        maxstars = 40

        names = data.keys()
        names.sort()
        
        for name in names:
            avgs = data[name]
            if name == 'labels': continue
            print name
            print "=============="

            for label, y in zip(xs, avgs):

                nstars = int(20 * y / maxy)
                    
                print label.rjust(9), '*' * nstars

            print
            print "enter to continue or 'x' to exit"
            if 'x' in sys.stdin.readline():
                break


class RepliesByHour(object):
    #set default options so that email = "" --> might need to change this
    def get_sql(self, lat=True, reply=True, start=None, end = None, daysofweek = None, email="", currid=None):
        WHERE = []
        
        #URGENT: Need to also deal with multiple users and accounts
        WHERE.append("l.account = %d" % currid)

        #set the upperbound on the emails to consider for latency - if the response didn't come within 60 hrs then don't consider those responses
        WHERE.append("l.lat < 60*60*60 AND l.lat > 0")

        if start:
            WHERE.append("origdate > '%s'::timestamp" % start.strftime('%Y-%m-%d'))

        if end:
            WHERE.append("origdate < '%s'::timestamp" % end.strftime('%Y-%m-%d'))

        if reply is None:
            WHERE.append("(me.id = l.replier or me.id = l.sender)")

        elif reply:
            WHERE.append("me.id = l.replier")

        else:
            WHERE.append("me.id = l.sender")

        if email:
            WHERE.append("me.email like '%s'" % email)

        if lat:
            SELECT = "avg(lat)/60/60 as avglat, date_part('hour', origdate) as hour"

        else:
            SELECT = "count(*),  extract('hour' from origdate) as hour"
        WHERE = ' and '.join(WHERE)
        
        sql = "SELECT %s FROM latencies l, contacts me WHERE %s GROUP BY hour ORDER BY hour asc;" % (SELECT, WHERE)

        return sql



###############
#NOT SURE WEHRE THIS CLASS IS USED. DO WE NEED TO DELETE THIS?
###############
#class EveryoneByHour(object):
#    def get_sql(self, lat=True, start=None, end = None, daysofweek = None):
#        WHERE = []
#        WHERE.append("l.lat < 1")
#        if start:
#            WHERE.append("datetime(sentdate) > datetime('%s')" % start.strftime('%Y-%m-%d'))
#        if end:
#            WHERE.append("datetime(sentdate) < datetime('%s')" % end.strftime('%Y-%m-%d'))
#        if daysofweek:
#            WHERE.append("strftime('%%w', sentdate) in (%s)" % (','.join(map(lambda x: "'%s'" % x, daysofweek))))
#            print WHERE[-1]

#        if lat:
#            SELECT = "avg(lat) as avglat, strftime('%H', sentdate) as hour"#, CAST(strftime('%M', sentdate)/60 as integer) as minute"
#        else:
#            SELECT = "count(*), strftime('%H', sentdate) as hour"#, CAST(strftime('%M', sentdate)/60 as integer) as minute"

#        WHERE = ' and '.join(WHERE)

#        sql = "SELECT %s FROM latency l WHERE %s GROUP BY hour ORDER BY hour asc;" % (SELECT, WHERE)
#        return sql




    


if __name__ == '__main__':
    import json

    genqs = EveryoneByHour()
    queries = []

    for month in xrange(12):
        month += 1
        start = date(2010, month, 1)
        end = start + timedelta(days=30)
        #queries.append(('Count 2011 %d' % month, stats.get_sql(lat=False, reply=None, start=start, end = end)))
        queries.append(('Count 2011 %d' % month, genqs.get_sql(lat=True, start=start, end = end)))

    foo = LineData()
    conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    data = foo.get_data(queries, conn)
    foo.viz(data)
    print json.dumps(data)
        
        

