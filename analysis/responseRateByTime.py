from optparse import OptionParser
import random, smtplib, sys, time, urllib
import sqlite3, email, math, imaplib
from dateutil.parser import parse
from datetime import timedelta, datetime, time, date
import json

import re

###########################################################
## KNOWN ISSUES:
## (1) If someone responds to the same email twice, then we count it as two
##     replies.  This is wrong, it should be counted once.  We currently cap
##     the aggregate % as 100% but this is not the ideal solution - there needs
##     to be a change made to the SQL query.
## (2) I don't like the e-mail ilike thing, because how often do people have
##     e-mail addresses that are similar to each other?  E.g. I (ravi) have
##     ravdawg@gmail.com and ravipatel@alum.mit.edu, which i don't think would
##     show up as being similar to each other.
##     The solution for this is to have an option on the front end that allows
##     a user to select multiple e-mail addresses for a particular individual.
##     Then, this script should then somehow map all those e-mails appropriately
##     to get the desired answer. - I totally agree with this (CPF). I think 
##     that everything should be user@mail.com format.
###########################################################


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
#########################################################
# HELPER FUNCTIONS
# 
# make_human_readble(mode, ind) - converts the index of the vector to a 
#                                 readable string, depending on the mode
# get_index(mode, thetime)      - gets the appropriate list index given the
#                                 email timestamp
# 
# HELPER CLASSES
# 
# Datum                         - is essentially a pair of integers. Stores #
#                                 of e-mails sent and replied to.
# ModeDatum                     - is a map of an 'index' to a Datum object
#                                 the 'index' is either the hour of the day 
#                                 or the day of the week.
#                                 helper functions exist to edit the counts in
#                                 the Datum objects within the map
#                                 returnJsonDictionary exists to spit out the
#                                 answer in Json format
#                                 
# For info on get_response_rate, scroll down to the function for the readme
#
##########################################################
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
    
    #if not in the mode day then label as time of the day
    indStr = "%2d" % ind
    ampm = ""
    if ind > 12:
        ampm = " PM"
        indStr = "%d" % (ind - 12)
    elif ind == 0:
        indStr = "Midnight"
    else:
        indStr = "%d" % ind
        ampm = " AM"
    indStr += ampm
    if indStr == "12 AM":
        indStr = "Noon"
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

        #cap all the data at 100% --> if a person replies twice to the same email original calculation will make 200%. This adjusts so that it becomes 100%
        if float(self.numReplied)/float(self.numSent) * 100 > 100:
            return 100
        else:
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
#############################################################
##
## get_response_rate is the main function.  It takes the following inputs:
## 
## mode - either "day" or "hour", will bucket emails either by day of week or
##        by hour
## 
## start - start date in format YYYY-MM-DD
## end   - end date in format YYYY-MM-DD
## 
## emailAddy - This is the e-mail address of the SENDER.  So, if jsmith@gmail 
##             was logged into inboxdr, he might want to see how often people
##             respond to his e-mails.  In this case, emailAddy should be set
##             to jsmith@gmail.  However, if he wants to see how often he
##             responds to emails from jdoe@aol then emailAddy should be set
##             to jdoe@aol and replyAddy (next argument, see below) should be
##             set to jsmith@gmail.
##             
## replyAddy - This is the e-mail address of the person replying to your emails.
##             So if kbryant@hotmail wants to see how often diesel@yahoo 
##             responds to his emails, emailAddy = kbryant@hotmail and 
##             replyAddy is set to diesel@yahoo.  If kbryant@hotmail wants to
##             see how often everyone responds to him, then replyAddy MUST
##             be set to the string ALL
## conn      - Database connection
##
##
## Possible user inputs and what they do:
## [...] day 2011-01-01 2012-01-01 ravdawg@gmail.com farm.cp@gmail.com 
##           -->  Selects all e-mails bucketed by day of week from beginning of 2011.  Selects e-mails that
##                ravdawg@gmail.com sent to farm.cp@gmail.com
## [...] day 2011-01-01 2012-01-01 ravdawg@gmail.com ALL
##           -->  Selects all e-mails bucketed by day of week from beginning of 2011.  Selects all e-mails that 
##                I sent and calculates how often I was responded to.  Note that if I send one e-mail to A and B
##                that will count as two separate sent e-mails, so that if only A responds, my rate is 50%.
## [...] day 2011-01-01 2012-01-01 farm.cp@gmail.com ravdawg@gmail.com
##           -->  Selects all e-mails bucketed by day of week from beginning of 2011.  Selects all e-mails that
##                farm.cp@gmail.com sent to ravdawg@gmail.com (note that ravdawg@gmail.com is the active user
##                on inboxdr).
## [...] day 2011-01-01 2012-01-01 farm.cp@gmail.com ALL
##           -->  Do NOT do this.  This will look at all e-mails that farm.cp@gmail.com sent to you, but if 
##                he also CC'ed other people on the same e-mails, then it will count those other CC'ed users
##                in the denominator.  We do not want that shit!  NEVER do this.  If you want to see how often
##                you responded to farm.cp@gmail.com, use the 3rd example.
##
##############################################################
def get_response_rate(mode, start, end, emailAddy, replyAddy, conn):
    if replyAddy == "ALL":
        SINGLE_REPLIER = False
    else:
        SINGLE_REPLIER = True
    typeMap = dict()
    typeMap["tos"] = ModeDatum(mode)
   # typeMap["ccs"] = ModeDatum(mode)
   # typeMap["bccs"] = ModeDatum(mode)
   # conn = sqlite3.connect('../mail.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()

    #try:
    if True:
        #this is the new postgres query
        c.execute("select id from contacts where email ilike %s;", ('%%%s%%' % emailAddy,))
        myid = int(c.fetchone()[0])

        if SINGLE_REPLIER:

            #this is the new postgres query
            #it allows for users to filter by person for that specific user's contact list. it accounts for overlaps of contacts between users (i.e. it is possible for two users to have a similar contact)

            idsql = """select id from contacts where email like '%s' 
                       and owner_id = 
                         (select id from auth_user where username = '%s')""" % (replyAddy, emailAddy)

            c.execute(idsql)

            replid = int(c.fetchone()[0])

        for tbl,trgt in typeMap.items():
            msgIds = []

            #needs to accept email accounts to distinguish between users --> executable SQL query for the denominator
            execCode_Denominator = "select emails.date, emails.id, emails.subj from emails inner join %s on emails.id = %s.email_id and emails.account = (select id from auth_user where username = '%s') and emails.date >= '%s' and emails.date <= '%s' " % (tbl, tbl, emailAddy, start, end)

            if SINGLE_REPLIER:
            #    execCode_Denominator += " and %s.contact_id = %d" % (tbl, replid)
                execCode_Denominator += " and %s.contact_id = %d " % (tbl, replid)

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
            
            #create numerator sql query
            execCode_Numerator = "select thedate, intid, e.id from ((select emails.id as intid, emails.date as thedate, emails.mid as msgid from %s inner join emails on %s.email_id = emails.id and emails.account = (select id from auth_user where username = '%s') and emails.date >= '%s' and emails.date <= '%s') as m left outer join emails as e on msgid = e.reply) where e.reply is not NULL " % (tbl, tbl,emailAddy, start, end)

            if SINGLE_REPLIER:
                #if this is for a specific person, then find the id it's from and add to the sql query
                execCode_Numerator += " and e.fr = %d " % replid

            #execute the code for the numerator
            c.execute(execCode_Numerator)
            res = c.fetchall()

            msgIds = []
            for item in res:
                msgIndex = "%s.%s" % (item[1], item[2])
                if msgIndex in msgIds:
                    continue
                msgIds.append(msgIndex)
                trgt.addReplied(get_index(mode, item[0]), 1)
    # except Exception, e:
    #     print "Caught exception"
    #     print >> sys.stderr, e

    #return the json dictionary
    return typeMap["tos"].returnJsonDictionary()


if __name__ == "__main__":

    mytable = get_response_rate(mymode, startD, endD)

    for typ,tbl in mytable.items():
        print typ
        tbl.printMe()
