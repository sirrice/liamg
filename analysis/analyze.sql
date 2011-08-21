insert into latencies  (account, replier, sender, replyemail, origemail, replydate, origdate)
select m1.account, c1.id as replier, c2.id as sender, 
       m1.id as replyemail, m2.id as origemail, 
       m1.date as replydate, m2.date as origdate
from contacts c1, contacts c2, emails m1, emails m2 
where m1.id > m2.id and m1.reply = m2.mid and m1.reply is not null and 
      c1.id = m1.fr and c2.id = m2.fr and m1.account = %s and 
      m1.account = m2.account and m2.imapid > %s;



