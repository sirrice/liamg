from xoauth import GenerateXOauthString, OAuthEntity
import base64, hmac, imaplib
from optparse import OptionParser
import random, sha, smtplib, sys, time, urllib
import psycopg2 as pg
import email, math, threading
from dateutil.parser import parse
from datetime import datetime, timedelta



import re
#refs_pat = '<(?P<ref>[\w+-=%#\.]+@([\w_]+.)*[\w_]+)>'
refs_pat = '<?(?P<ref>.+)>?'
refs_prog = re.compile(refs_pat)
contacts_pat = '(([\"\']?(?P<realname>\w[\w\ ]*)[\"\']?)?\s+)?<?(?P<email>[\w.]+@([\w_]+.)+[\w_]+)>?'
contacts_prog = re.compile(contacts_pat)


def download_headers(account, passw, conn, chunk=1000.0, maxmsgs=None):
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
    label_string = "[Gmail]/All Mail"
    search_string = "(SINCE 1-Jan-2009)"

    user = account.user
    host = account.host
    
    imap_conn = imaplib.IMAP4_SSL(account.host)
    imap_conn.debug = 0
    #imap_conn.authenticate('XOAUTH', lambda x: xoauth_string) not going to use oauthentication

    imap_conn.login(user.username, passw)
    imap_conn.select(label_string)
    typ, dat = imap_conn.search(None, search_string)
    iternum = 0

    # profiling information
    dlcost = 0.0
    dbcost = 0.0
    

    mids = sorted(map(int, dat[0].split()))
    if account.max_dl_mid != -1:
        mids = filter(lambda mid: mid > account.max_dl_mid, mids)
    account.max_mid = max(mids)
    if account.refreshing: return
    account.refreshing = True
    account.save()

    d = None
    print '%d total messages left' % len(mids)

    try:
        for idx in xrange(0, int(math.ceil(float(len(mids))/chunk))):
            curids = mids[int(idx*chunk):int((idx*chunk)+chunk)]

            start = time.time()
            typ, dat = imap_conn.fetch(','.join(map(str,curids)), '(RFC822.HEADER)')
            dlcost += time.time() - start

            print "processing messages %d - %d" % (idx*chunk, min((idx+1) * chunk,len(mids)))
            start = time.time()
            for d in dat:
                if d == ')': continue
                mid = int(d[0][:d[0].find(' ')])


                cur = conn.cursor()
                try:            
                    if proc_msg(cur, account, mid, d) is not None:
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
            download_headers(self.account, self.password, self.conn, self.chunk, self.maxmsgs)
            self.account.refreshing = False
            self.account.save()
        except:
            pass
        finally:
            self.conn.close()

    

    
    

if __name__ == '__main__':
    from settings import *
    import getpass
    import sys, os
    ROOT = os.path.abspath('%s/liamgwebapp/' % os.path.abspath(os.path.dirname(__file__)))
    sys.path.append(ROOT)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'liamgwebapp.settings'
    from django.contrib.auth.models import User
    from django.contrib.auth import authenticate
    from emailanalysis.models import *
    
    conn = pg.connect(database='liamg', user='liamg', password='liamg')
    #conn = sqlite3.connect('./mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    #setup_db(conn)
    
    
    # consumer = OAuthEntity('anonymous', 'anonymous')
    # access_token = OAuthEntity(token, secret)
    # xoauth_string = GenerateXOauthString(consumer, access_token, gmailaddr, 'imap',
    #                                      None, None, None)
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

    download_headers(account, passw, conn, chunk=100, maxmsgs=None)
    conn.close()
