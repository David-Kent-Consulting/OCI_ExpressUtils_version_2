#! /usr/bin/sh
PATH=$PATH:$HOME/bin:/usr/local/bin
export PATH
inst=`echo $1 | tr '[a-z]' '[A-Z]'`
ORAENV_ASK=NO
ORACLE_SID=$inst
# echo $ORAENV_ASK $ORACLE_SID
cd
. /usr/local/bin/oraenv
PID=`ps -fu oracle | grep ora_pmon_$ORACLE_SID | grep -v grep | tr ' ' '_'`
if [ X$PID = X ] ; then
   echo '***' Oracle instance $inst not running
   exit 0
   fi
echo '***' stopping $inst
sqlplus <<!!!
/ as sysdba
-- shutdown abort
-- startup restrict
shutdown immediate
quit
!!!
echo 'Oracle down' $inst `date` >> /home/oracle/logs/ora_start_stop_log
