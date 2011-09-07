from optparse import OptionParser
import random, smtplib, sys, time, urllib
import sqlite3, email, math, imaplib
from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import json

import re

#modes = ["day", "hour"]

#mymode = sys.argv[1]
#if mymode not in modes:
#    sys.stderr.write("invalid mode!: %s\n" % mymode)
#    exit(1)
#startD = sys.argv[2]
#endD = sys.argv[3]
#emailAddy = sys.argv[4]
#replyAddy = ""
#SINGLE_REPLIER = False
#if len(sys.argv) > 5:
#    SINGLE_REPLIER = True
#    replyAddy = sys.argv[5]

#startDT = parse(startD)
#endDT = parse(endD)

def make_human_readable(mode, ind):
    if mode == "day":
        dayofweekMap = dict()
        dayofweekMap[0] = "Monday"
        dayofweekMap[1] = "Tuesday"
        dayofweekMap[2] = "Wednesday"
        dayofweekMap[3] = "Thursday"
        dayofweekMap[4] = "Friday"
        dayofweekMap[5] = "Saturday"
        dayofweekMap[6] = "Sunday"
        return dayofweekMap[ind]
    indStr = "%2d" % ind
    ampm = " AM"
    if ind >= 12:
        ampm = " PM"
        indStr = "%02d:00" % (ind - 11)
    elif ind == 0:
        indStr = "12:00"
    else:
        indStr = "%02d:00" % ind
    indStr += ampm
    return indStr

def get_index(mode, thetime):
    #thetime = parse(thetime)
    if mode == "day":
        ret = thetime.weekday()
    else:
        ret = thetime.hour
    return ret

class Datum:
    def __init__(self):
        self.numSent = 0
        self.numReplied = 0
    def getResponseRate(self):
        if self.numSent == 0:
            return 0.0
        return float(self.numReplied) / float(self.numSent) * 100.0 

class ModeDatum:
    def __init__(self, themode):
        self.masterMap = dict()
        self.thismode = themode
        num = 24
        if themode == "day":
            num = 7
        for i in range(num):
            self.masterMap[i] = Datum()
        self.MAX_INDEX = num
    def addSent(self, ind, num):
        if ind > self.MAX_INDEX:
            return
        self.masterMap[ind].numSent += num
    def addReplied(self, ind, num):
        if ind > self.MAX_INDEX:
            return
        self.masterMap[ind].numReplied += num
    def printMe(self):
        for i in range(self.MAX_INDEX):
            indexStr = make_human_readable(self.thismode, i)
            rt = self.masterMap[i].getResponseRate()
            print "%9s %6d %6d %6.2f%% %s" % (indexStr, self.masterMap[i].numSent, self.masterMap[i].numReplied, rt, "*"*int(rt / 5.0))
    def returnJsonDictionary(self):
        ret = dict()
        ret["labels"] = []
        ret["y"] = []
        for key,vals in self.masterMap.items():
            ret["labels"].append(make_human_readable(self.thismode, key))
            ret["y"].append(vals.getResponseRate())

        return ret

def get_response_rate(mode, start, end, emailAddy, replyAddy, conn):
    if replyAddy == "":
        SINGLE_REPLIER = False
    else:
        SINGLE_REPLIER = True
    typeMap = dict()
    typeMap["tos"] = ModeDatum(mode)
   # typeMap["ccs"] = ModeDatum(mode)
   # typeMap["bccs"] = ModeDatum(mode)
   # conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()

    print emailAddy
    try:
        #DEPRECATED: this is the sqlite query that is no longer used
        #myid = int(c.execute("select id from contacts where email = '%s';" % emailAddy).fetchone()[0])

        #this is the new postgres query
        c.execute("select id from contacts where email = '%s';" % emailAddy)
        myid = int(c.fetchone()[0])

        if SINGLE_REPLIER:
            #DEPRECATED: this is the sqlite query that is no longer used
            #replid = int(c.execute("select id from contacts where email = '%s';" % replyAddy).fetchone()[0])

            #this is the new postgres query
            c.execute("select id from contacts where email = '%s';" % replyAddy)
            replid = int(c.fetchone()[0])

        for tbl,trgt in typeMap.items():
            msgIds = []
            execCode_Denominator = "select emails.date,emails.id,emails.subj from emails inner join %s on emails.id = %s.email_id and emails.fr = %d and emails.account = (select id from auth_user where username = '%s') and emails.date >= '%s' and emails.date <= '%s'" % (tbl, tbl, myid, emailAddy, start, end)

            if SINGLE_REPLIER:
                execCode_Denominator += " and %s.contact_id = %d" % (tbl, replid)

            #DEPRECATED: this is the sqlite query that is no longer used
            #res = c.execute(execCode_Denominator).fetchall()
            
            #execute the postgres numerator query and push to the res
            c.execute(execCode_Denominator)
            res = c.fetchall()

            for item in res:
                if SINGLE_REPLIER and int(item[1]) in msgIds:
                    continue
                msgIds.append(int(item[1]))
                trgt.addSent(get_index(mode, item[0]), 1)
            addlString = ""
            if SINGLE_REPLIER:
                addlString = " and %s.contact_id = %d" % (tbl, replid)
            execCode_Numerator = "select thedate,intid,e.id from ((select emails.id as intid, emails.date as thedate,emails.mid as msgid from %s inner join emails on %s.email_id = emails.id and emails.fr = %d%s and emails.account = (select id from auth_user where username = '%s') and emails.date >= '%s' and emails.date <= '%s') as m left outer join emails as e on msgid = e.reply) where e.reply is not NULL " % (tbl, tbl,myid, addlString, emailAddy, start, end)
            if SINGLE_REPLIER:
                execCode_Numerator += " and e.fr = %d" % replid

            #DEPRECATED
            #res = c.execute(execCode_Numerator).fetchall()

            c.execute(execCode_Numerator)
            res = c.fetchall()

            msgIds = []
            for item in res:
                msgIndex = "%s.%s" % (item[1], item[2])
                if msgIndex in msgIds:
                    continue
                msgIds.append(msgIndex)
                trgt.addReplied(get_index(mode, item[0]), 1)
    except Exception, e:
        print "Caught exception"
        print >> sys.stderr, e
    return typeMap["tos"].returnJsonDictionary()


if __name__ == "__main__":

    mytable = get_response_rate(mymode, startD, endD)

    for typ,tbl in mytable.items():
        print typ
        tbl.printMe()
