
from xoauth import GenerateXOauthString, OAuthEntity
import base64, hmac, imaplib
from optparse import OptionParser
import random, sha, smtplib, sys, time, urllib
import psycopg2 as pg
import email, math, threading
from dateutil.parser import parse
from datetime import datetime, timedelta
import pyparsing
from pyparsing import (nestedExpr, Literal, Word, alphanums, 
                       quotedString, replaceWith, nums, removeQuotes)



import re
#refs_pat = '<(?P<ref>[\w+-=%#\.]+@([\w_]+.)*[\w_]+)>'
refs_pat = '<?(?P<ref>.+)>?'
refs_prog = re.compile(refs_pat)
contacts_pat = '(([\"\']?(?P<realname>\w[\w\ ]*)[\"\']?)?\s+)?<?(?P<email>[\w.]+@([\w_]+.)+[\w_]+)>?'
contacts_prog = re.compile(contacts_pat)
# body structure parser
NIL = Literal("NIL").setParseAction(replaceWith(None))
integer = Word(nums).setParseAction(lambda t:int(t[0]))
quotedString.setParseAction(removeQuotes)
content = (NIL | integer | Word(alphanums))
ne = nestedExpr(content=content, ignoreExpr=quotedString)
bs_parser = ne


def parse_bs(bs):
    try:
        # remove body header content, and close tag
        bs = bs[:bs.rfind('BODY[HEADER]')] + ')'
        # remove outer layer
        bs = bs[ bs.find("(BODYSTRUCTURE") + len("(BODYSTRUCTURE"):bs.rfind(')')].strip()
        ps = bs_parser.parseString(bs)
        struct = ps[0]
        return struct
    except:
        pass


def find_text(bs, prefix=''):
    if isinstance(bs, pyparsing.ParseResults):
        if bs[0] == 'TEXT' and bs[1] == 'PLAIN':
            if prefix == '':
                section = 'TEXT'
            else:
                section = prefix[1:]
            return section
        else:
            i = 1
            for x in bs:
                ret = find_text(x, '%s.%d' % (prefix, i))
                if ret is not None: return ret
                i += 1

def execute_latencies(actid, conn):
    #make a cursor object to execute the sql script
    ##latency is the difference between m1.date and m2.date

    c = conn.cursor()
     #fill the latencies table
    latencies_sql = """INSERT into latencies
                    (account, replier, sender, replyemail, origemail, replydate, origdate, lat)
                    SELECT m1.account, c1.id as replier, c2.id as sender,
                           m1.id AS replyemail, m2.id AS origemail,
                           m1.date AS replydate, m2.date AS origdate,
                           (extract (epoch from m1.date::timestamp) - extract(epoch from m2.date::timestamp)) AS lat
                    FROM contacts c1, contacts c2, emails m1, emails m2
                    WHERE m1.id > m2.id AND m1.reply = m2.mid AND
                          c1.id = m1.fr AND c2.id = m2.fr AND m1.account = %s AND
                          m1.account = m2.account;""" % (actid)

    
    #commit the data
    c.execute(latencies_sql)
    conn.commit()


    

def download_headers(account, passw, conn, chunk=1000.0, maxmsgs=None, gettext=True):
    """
    connect to gmail and download all headrs since jan-2011
    
    select gmail label:
     INBOX
     [Gmail]/All Mail
     [Gmail]/Sent Mail

    search examples:
     (ALL)
     (BEFORE 20-Apr-2010 SINCE 1-Apr-2010)
     (SUBJECT "atwoods")
     (SINCE 01-Jan-2011)
    """

##The search string will only download for the year. This will shorten the download time that users will have
##Will eventually need to implement a better algorithm to refresh this while a
##user is looking at the data on the front end.
    label_string = "[Gmail]/All Mail"
    search_string = "(SINCE 1-Jan-2011)"

    user = account.user
    host = account.host
    
    imap_conn = imaplib.IMAP4_SSL(account.host)
    imap_conn.debug = 0
    #imap_conn.authenticate('XOAUTH', lambda x: xoauth_string) not going to use oauthentication
    try:
        imap_conn.login(user.username, passw)
        imap_conn.select(label_string)
    except Exception, err:
        import traceback
        print >> sys.stderr, err
        traceback.print_tb(sys.exc_info()[2])
        print >> sys.stderr, ''
        return False


    #get the data from the imap search using the search string
    typ, dat = imap_conn.search(None, search_string)
    iternum = 0

    # profiling information
    dlcost = 0.0
    dbcost = 0.0
    

    mids = sorted(map(int, dat[0].split()))
    if account.max_dl_mid != -1:
        mids = filter(lambda mid: mid > account.max_dl_mid, mids)
    if len(mids) == 0:
        print "no messages left"
        return
    account.max_mid = max(mids)
    account.save()

    d = None
    print '%d total messages left' % len(mids)

    try:
        for idx in xrange(0, int(math.ceil(float(len(mids))/chunk))):
            curids = mids[int(idx*chunk):int((idx*chunk)+chunk)]
            print "processing messages %d - %d" % (idx*chunk, min((idx+1) * chunk,len(mids)))

            
            start = time.time()
            typ, dat = imap_conn.fetch(','.join(map(str,curids)), '(BODY.PEEK[HEADER] BODYSTRUCTURE)')
            dlcost += time.time() - start

            start = time.time()
            for d in dat:
                if d == ')': continue
                mid = int(d[0][:d[0].find(' ')])


                cur = conn.cursor()
                try:            
                    if proc_msg(cur, account, mid, d) is not None:
                        if gettext:
                            add_email_text(cur, imap_conn, mid, d[0])
                        
                        account.max_dl_mid = mid
                        account.save()
                        iternum += 1
                        conn.commit()

                except Exception, err:
                    import traceback
                    print >> sys.stderr, "=== msg: %d ===" % mid
                    print >> sys.stderr, err
                    traceback.print_tb(sys.exc_info()[2])
                    print >> sys.stderr, ''
                    print >> sys.stderr, d
                    print >> sys.stderr, ''
                    conn.rollback()
                finally:
                    cur.close()

                if maxmsgs and iternum >= maxmsgs: break

            dbcost += time.time() - start
            if maxmsgs and iternum >= maxmsgs: break
            

    except Exception, err:
        import traceback
        print >> sys.stderr, err
        traceback.print_tb(sys.exc_info()[2])
        print >> sys.stderr, ''

    account.refreshing = False
    account.last_refresh = datetime.now()
    account.save()
    print "download time: %f" % dlcost
    print "database time: %f" % dbcost



def add_email_text(cur, imap_conn, mid, bs_str):
    bs = parse_bs(bs_str)
    if not bs: return False
    section = find_text(bs)
    if section:
        t,d = imap_conn.fetch(str(mid), '(body.peek[%s])' % section)
        e = email.message_from_string( d[0][1])
        text = e.get_payload()
        
        text = text.replace('\n\r', '\n').replace("\r", '')
        cur.execute("insert into contents (emailid, text) values (%s,%s)", (mid, text))

        return True
    return False
                            


# check if username/password combo is valid
def authenticate_login(imap_hostname, user, passw):
    imap_conn = imaplib.IMAP4_SSL(imap_hostname)
    imap_conn.debug = 0
    imap_conn.login(user, passw)


def proc_msg(cur, account, imapid, d):
    """
    clean and extract important header information, and store in database
    """
    if len(d) == 0: return None
    try:
        e = email.message_from_string(d[1])
    except Exception, e:
        return None
    
    
    multipart = e.is_multipart()
    to = extract_names(e.get('To', '')) 
    
    #break apart the headers of each email
    fr =  extract_names(e['From'])
    cc = extract_names(e.get('CC', ''))
    bcc = extract_names(e.get('BCC', ''))
    subj = e.get('Subject', '')
    date = clean_date(e['Date'])
    mid = extract_refs(e.get('Message-ID', ''))[0]
    replyto = extract_refs(e.get('In-Reply-To', ''))
    replyto = replyto and replyto[0] or None
    # References are all message IDs of parents in the reply tree
    refs = extract_refs(e.get('References',''))
        
    try:
        if not len(get_tuples(cur, "emails", "mid", mid)):
            add_msg(cur, account, fr[0], subj, date, imapid, mid,
                    replyto, multipart, to, cc, bcc, refs)
        
        
        return True
    except Exception, err:
        import traceback
        print >> sys.stderr, err
        traceback.print_tb(sys.exc_info()[2])
        print

        print "===header info==="
        print "From:"
        print "\t", fr[0]
        print subj
        print date
        print replyto
        print "Tos: "
        for x in to: print "\t", x
        print "CCs: "
        for x in cc: print "\t", x
        print "BCCs: "
        for x in bcc: print "\t", x
        print "Refs: "
        for x in refs: print "\t", x

        raise RuntimeError
        


def clean_date(txt):
	if '(' in txt:
		txt = txt[:txt.index('(')]
	return parse(txt)

def clean(txt):
	return txt.replace('\r\n',',')

def extract_refs(txt):
    txt = clean(txt)
    refs = []
    for block in txt.strip(' ,').split(','):
        res = refs_prog.search(block)
        if res:
            refs.append(res.group('ref'))
    return refs
    

#extract names from the headers of each email- assume separated by comma
def extract_names(txt):
    txt = clean(txt)
    emails = set()
    contacts = []
    for block in txt.strip(' ,').split(','):
        res = contacts_prog.search(block)
        if res:
            name = res.group('realname')
            email = res.group('email')
            if email: email = email.lower()
            if email in emails: continue
            emails.add(email)
            contacts.append((name, email))
        
    return contacts



def get_tuple(c, table, id):
    try:
        c.execute('select * from %s where id = %%s' % table, (id,))
        res = c.fetchone()
    except Exception, e:
        print >> sys.stderr, "%s\tid=%s" % (table, id)
        res = None
    return res

def get_tuples(c, table, attr, id):
    ret = []
    try:
        c.execute('select * from %s where %s = %%s' % (table, attr), (id,))
        ret.extend(c.fetchall())
    except Exception, e:
        print >> sys.stderr, "%s\t%s=%s" % (table, attr, id)
        ret = []
    return ret
    

def get_email(c, id):
    return get_tuple(c, "contacts", id)

def get_msg(c, id):
    return get_tuple(c, "emails", id)



def add_msg(c, account, fr, subj, date, imapid, mid, reply, multipart, to, cc, bcc, refs):
    frid = add_email(c, account, fr[0], fr[1])

    c.execute('insert into emails values (DEFAULT, %s,%s,%s,%s,%s,%s,%s,%s) returning id', (account.pk, frid, subj, str(date), imapid, mid, reply, multipart))
    msgid = c.fetchone()[0]
    for name, email in to:
        c.execute('insert into tos values (DEFAULT, %s, %s)', (msgid, add_email(c, account, name, email)))
    for name, email in cc:
        c.execute('insert into ccs values (DEFAULT, %s, %s)', (msgid, add_email(c, account, name, email)))
    for name, email in bcc:
        c.execute('insert into bccs values (DEFAULT, %s, %s)', (msgid, add_email(c, account, name, email)))
    for ref in refs:
        c.execute('insert into refs values (DEFAULT, %s, %s)', (msgid, ref))

    return msgid


def add_email(c, account, name, email):
    if not email: return
    uid = account.user.pk
    # first check if the email exists.  contact.email column should be unique
    c.execute('select id, name from contacts where owner_id = %s and email = %s', (uid, email,))
    row = c.fetchone()
    if row:
        # if it exists but the name was null, update with actual name value
        rowid = row[0]
        if not row[1] and name:
            c.execute("update contacts set name = %s where owner_id = %s and id = %s", (name, uid, rowid))
    else:
        # otherwise insert a new contact info
        c.execute("insert into contacts values (DEFAULT,%s,%s,%s) returning id", (uid, name, email))
        rowid = c.fetchone()[0]
    return rowid


# def setup_db(conn):
#     c = conn.cursor()
#     try:
#         c.execute('''create table contacts (id INTEGER PRIMARY KEY AUTOINCREMENT,
#         name text, email text not null)''')
#         c.execute('''create table msgs (id integer primary key autoincrement,
#         fr int references contacts(id), subj text, date datetime, mid text unique,
#         reply text references msgs(mid), multipart bool)''')
#         c.execute('''create table refs (id integer primary key autoincrement,
#         msg int references msgs(id), refed text references msgs(mid) )''')
#         c.execute('''create table tos (id integer primary key autoincrement,
#         msg int references msgs(id), cid int references contacts(id) )''')
#         c.execute('''create table ccs (id integer primary key autoincrement,
#         msg int references msgs(id), cid int references contacts(id) )''')
#         c.execute('''create table bccs (id integer primary key autoincrement,
#         msg int references msgs(id), cid int references contacts(id) )''')
#         conn.commit()
#     except Exception, e:
#         conn.rollback()
#         print >> sys.stderr, e
#     c.close()




class AsyncDownload(threading.Thread):
    
    def __init__(self, account, passw, conn, chunk=1000.0, maxmsgs=None):
        super(AsyncDownload, self).__init__()
        self.password = passw
        self.conn = conn
        self.chunk=chunk
        self.maxmsgs = maxmsgs
        self.account = account
        
    def run(self):
        try:
            print "running asyncdownload"
            if account.refreshing: return
            account.refreshing = True
            account.save()
            download_headers(self.account, self.password, self.conn, self.chunk, self.maxmsgs)
            self.account.refreshing = False
            self.account.save()
        except:
            pass
        finally:
            self.conn.close()

    

    
    

if __name__ == '__main__':
    import getpass
    import sys, os
    ROOT = os.path.abspath('%s/liamgwebapp/' % os.path.abspath(os.path.dirname(__file__)))
    sys.path.append(ROOT)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'liamgwebapp.settings'
    from settings import *    
    from django.contrib.auth.models import User
    from django.contrib.auth import authenticate
    from emailanalysis.models import *
    
    conn = pg.connect(database='liamg', user='liamg', password='liamg')
    
    # consumer = OAuthEntity('anonymous', 'anonymous')
    # access_token = OAuthEntity(token, secret)
    # xoauth_string = GenerateXOauthString(consumer, access_token, gmailaddr, 'imap',
    #                                      None, None, None)
    if len( sys.argv ) >= 3:
        username = sys.argv[1]
        passw = sys.argv[2]
    else:
        print "enter your gmail email and password!"
        sys.stdout.write("Username: ")
        sys.stdout.flush()
        username = sys.stdin.readline().strip()
        passw = getpass.getpass("Password: ")

    user = authenticate(username=username, password=passw)
    if not user:
        user = User.objects.create_user(username, username, passw)
        account = Account(user=user, host="imap.googlemail.com", username="username")
        account.save()
    else:
        account = Account.objects.get(user=user)

    download_headers(account, passw, conn, chunk=1000, maxmsgs=None, gettext=True)
    conn.close()
