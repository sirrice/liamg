from xoauth import GenerateXOauthString, OAuthEntity
import base64, hmac, imaplib
from optparse import OptionParser
import random, sha, smtplib, sys, time, urllib
import sqlite3, email, math
from dateutil.parser import parse
from datetime import timedelta


import re
refs_pat = '<(?P<ref>[\w+-=%]+@([\w_]+.)*[\w_]+)>'
refs_prog = re.compile(refs_pat)
contacts_pat = '(([\"\']?(?P<realname>\w[\w\ ]*)[\"\']?)?\s+)?<?(?P<email>[\w.]+@([\w_]+.)+[\w_]+)>?'
contacts_prog = re.compile(contacts_pat)


def download_headers(imap_hostname, user, xoauth_string, conn):
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
    search_string = "(ALL)"

    
    imap_conn = imaplib.IMAP4_SSL(imap_hostname)
    imap_conn.debug = 0
    imap_conn.authenticate('XOAUTH', lambda x: xoauth_string)
    imap_conn.select(label_string)
    typ, dat = imap_conn.search(None, search_string)
    iternum = 0
    chunk = 1000.0

    mids = sorted(map(int, dat[0].split()), reverse=True)
    print '%d total messages' % len(mids)
    for idx in xrange(0, int(math.ceil(float(len(mids))/chunk))):
        curids = mids[int(idx*chunk):int((idx*chunk)+chunk)]
        typ, dat = imap_conn.fetch(','.join(map(str,curids)), '(RFC822.HEADER)')

        print "processing messages %d - %d" % (idx*chunk, min((idx+1) * chunk,len(mids)))
        for d in dat:
            proc_msg(conn, d)



def proc_msg(conn, d):
    """
    clean and extract important header information, and store in database
    """
    if len(d) == 0: return
    try:
        e = email.message_from_string(d[1])
    except Exception, e:
        return False
    try:
        multipart = e.is_multipart()
        to = extract_names(e['To']) 
        fr =  extract_names(e['From'])
        cc = extract_names(e.get('CC', ''))
        bcc = extract_names(e.get('BCC', ''))
        subj = e.get('Subject', '')
        date = clean_date(e['Date'])
        mid = extract_refs(e.get('Message-ID', ''))[0]
        replyto = e.get('In-Reply-To', None)
        # References are all message IDs of parents in the reply tree
        refs = extract_refs(e.get('References',''))
        add_msg(conn, fr[0], subj, date, mid, replyto, multipart, to, cc, bcc, refs)
        return True
    except Exception, err:
        print >> sys.stderr, err
        print >> sys.stderr, e
        return False


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
    
def extract_names(txt):
    txt = clean(txt)

    contacts = []
    for block in txt.strip(' ,').split(','):
        res = contacts_prog.search(block)
        if res:
            name = res.group('realname')
            email = res.group('email')
            if email: email = email.lower()
            contacts.append((name, email))
    return contacts



def get_tuple(conn, table, id):
    c = conn.cursor()
    try:
        res = c.execute('select * from %s where id = ?' % table, (id,))
        res = res.fetchone()
    except Exception, e:
        print >> sys.stderr, e
        res = None
    c.close()
    return res

def get_tuples(conn, table, attr, id):
    c = conn.cursor()
    ret = []
    try:
        res = c.execute('select * from %s where %s = ?' % (table, attr), (id,))
        ret.extend(res)
    except Exception, e:
        print >> sys.stderr, e
        ret = []
    c.close()
    return ret
    

def get_email(conn, id):
    return get_tuple(conn, "contacts", id)

def get_msg(conn, id):
    return get_tuple(conn, "msgs", id)



def add_msg(conn, fr, subj, date, mid, reply, multipart, to, cc, bcc, refs):
    c = conn.cursor()

    frid = add_email(conn, fr[0], fr[1])
    c.execute('insert into msgs values (NULL, ?,?,?,?,?,?)', (frid, subj, str(date), mid, reply, multipart))
    msgid = c.lastrowid
    for name, email in to:
        c.execute('insert into tos values (NULL, ?, ?)', (msgid, add_email(conn, name, email)))
    for name, email in cc:
        c.execute('insert into ccs values (NULL, ?, ?)', (msgid, add_email(conn, name, email)))
    for name, email in bcc:
        c.execute('insert into bccs values (NULL, ?, ?)', (msgid, add_email(conn, name, email)))
    for ref in refs:
        c.execute('insert into refs values (NULL, ?, ?)', (msgid, ref))

    conn.commit()
    c.close()

def add_email(conn, name, email):
    if not email: return
    c = conn.cursor()
    try:
        # first check if the email exists.  contact.email column should be unique
        res = c.execute('select id, name from contacts where email = ?', (email,))
        row = res.fetchone()
        if row:
            # if it exists but the name was null, update with actual name value
            rowid = row[0]
            if not row[1] and name:
                c.execute("update contacts set name = ? where id = ?", (name, rowid))
        else:
            # otherwise insert a new contact info
            c.execute("insert into contacts values (NULL,?, ?)", (name, email))
            rowid = c.lastrowid
        conn.commit()
    except Exception, e:
        print >> sys.stderr, e
        conn.rollback()
        
    c.close()
    return rowid

def setup_db(conn):
    c = conn.cursor()
    try:
        c.execute('''create table contacts (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name text, email text not null)''')
        c.execute('''create table msgs (id integer primary key autoincrement,
        fr int references contacts(id), subj text, date datetime, mid text unique,
        reply text references msgs(mid), multipart bool)''')
        c.execute('''create table refs (id integer primary key autoincrement,
        msg int references msgs(id), refed text references msgs(mid) )''')
        c.execute('''create table tos (id integer primary key autoincrement,
        msg int references msgs(id), cid int references contacts(id) )''')
        c.execute('''create table ccs (id integer primary key autoincrement,
        msg int references msgs(id), cid int references contacts(id) )''')
        c.execute('''create table bccs (id integer primary key autoincrement,
        msg int references msgs(id), cid int references contacts(id) )''')
        conn.commit()
    except Exception, e:
        conn.rollback()
        print >> sys.stderr, e
    c.close()







    

    
    

if __name__ == '__main__':
    from settings import *

    conn = sqlite3.connect('./mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    setup_db(conn)
    
    consumer = OAuthEntity('anonymous', 'anonymous')
    access_token = OAuthEntity(token, secret)
    xoauth_string = GenerateXOauthString(consumer, access_token, gmailaddr, 'imap',
                                         None, None, None)
    download_headers('imap.googlemail.com', gmailaddr, xoauth_string, conn)
    conn.close()
