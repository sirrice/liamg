import sqlite3, email, math
from dateutil.parser import parse
from datetime import timedelta, datetime
import sys
import matplotlib.pyplot as plt
plt.ion()


def get_sent_histogram(conn, name):
    """
    example query that retrieves a per day count of emails to <name>
    """
    c = conn.cursor()
    ret = []
    try:
        query = "select date(date) as day, count(*) from msgs, contacts, tos where msgs.id = tos.msg and tos.cid = contacts.id and contacts.name like ? group by day order by day asc;"        
        res = c.execute(query, (''.join(['%',name,'%']),))
        # # counts per week
        for row in res:
            d = parse(row[0])
            d = d - timedelta(days=d.weekday())
            ndays = d - datetime(d.year, 1, 1) 
            count = row[1]
            if len(ret) and ret[-1][0] == d:
                ret[-1][1] += count
            else:
                ret.append([d, count])
        #ret.extend([(parse(row[0]),  row[1]) for row in res])
    except Exception, e:
        print e
        ret = []
    c.close()
    ret = map(tuple, ret)
    return ret

def print_chart(name):
    hist = get_sent_histogram(conn, name)

    day = start = datetime(day=1, month=1, year=2005)
    day = start = start - timedelta(days=start.weekday())
    end = datetime.now()
    d = dict(hist)
    daydelt = timedelta(days=7)

    xs, ys = [], []
    while day <= end:
        count = day in d and d[day] or 0
        xs.append(day)
        ys.append(count)
        day += daydelt

    plt.plot(xs, ys, 'r-')
    plt.ylim(0, max(50, max(ys) + 10))
    plt.show()
    plt.draw()
    

if __name__ == '__main__':
    
    conn = sqlite3.connect('./mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    print "enter part of a friend's name and I'll plot a histogram of your email to him/her"
    print "enter a blank line to exit"

    while True:
        sys.stdout.write("name: ")
        sys.stdout.flush()
        name = sys.stdin.readline().strip()
        if not name: break
        plt.cla()        
        plt.clf()
        print_chart(name)

    conn.close()



