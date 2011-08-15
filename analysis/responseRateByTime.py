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
        print ret
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
    try:
        myid = int(c.execute("select id from contacts where email = '%s';" % emailAddy).fetchone()[0])
        if SINGLE_REPLIER:
            replid = int(c.execute("select id from contacts where email = '%s';" % replyAddy).fetchone()[0])
        for tbl,trgt in typeMap.items():
            msgIds = []
            execCode_Denominator = "select msgs.date,msgs.id,msgs.subj from msgs inner join %s on msgs.id = %s.msg and msgs.fr = %d and msgs.date >= '%s' and msgs.date <= '%s'" % (tbl, tbl, myid, start, end)
            if SINGLE_REPLIER:
                execCode_Denominator += " and %s.cid = %d" % (tbl, replid)
            print(execCode_Denominator)
            res = c.execute(execCode_Denominator).fetchall()
            print res
            for item in res:
                if SINGLE_REPLIER and int(item[1]) in msgIds:
                    continue
                msgIds.append(int(item[1]))
                trgt.addSent(get_index(mode, item[0]), 1)
            addlString = ""
            if SINGLE_REPLIER:
                addlString = " and %s.cid = %d" % (tbl, replid)
            execCode_Numerator = "select thedate,intid,e.id from ((select msgs.id as 'intid',msgs.date as 'thedate',msgs.mid as 'msgid' from %s inner join msgs on %s.msg = msgs.id and msgs.fr = %d%s and msgs.date >= '%s' and msgs.date <= '%s') as m left outer join msgs as e on msgid = e.reply) where e.reply not NULL " % (tbl, tbl,myid, addlString, start, end)
            if SINGLE_REPLIER:
                execCode_Numerator += " and e.fr = %d" % replid
            res = c.execute(execCode_Numerator).fetchall()
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
