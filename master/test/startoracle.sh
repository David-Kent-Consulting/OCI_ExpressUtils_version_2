#! /usr/bin/sh
PATH=$PATH:$HOME/bin:/usr/local/bin
export PATH
inst=`echo $1 | tr '[a-z]' '[A-Z]'`
ORAENV_ASK=NO
ORACLE_SID=$inst
# echo $ORAENV_ASK $ORACLE_SID
. /usr/local/bin/oraenv
PID=`ps -fu oracle | grep ora_pmon_$ORACLE_SID | grep -v grep | tr ' ' '_'`
if [ X$PID != X ] ; then
   echo '***' Oracle instance $inst already running.
   exit 1
   fi
echo '***' starting $inst
sqlplus <<!!!
/ as sysdba
startup
quit
!!!
echo 'Oracle up' $inst `date` >> /home/oracle/logs/ora_start_stop_log