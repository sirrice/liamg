drop table if exists latency;
create table latency as 
select c1.id as replyuid, c2.id as senduid, 
       m1.id as replymid, m2.id as sendmid, 
       m2.date as sentdate, 
       (julianday(datetime(m1.date))-julianday(datetime(m2.date))) as lat 
from contacts c1, contacts c2, msgs m1, msgs m2 
where m1.id > m2.id and m1.reply = m2.mid and m1.reply not null and 
      c1.id = m1.fr and c2.id = m2.fr;



