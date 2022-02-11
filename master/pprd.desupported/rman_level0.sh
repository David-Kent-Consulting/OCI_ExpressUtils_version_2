[oracle@UVIDBT01 bin]$ cat rman_level0.sh
#! /bin/sh
#
# rman_level0.sh/rman_level1.sh (the two should be hard links to same file)
# makes a level-0 or level-1 backup of an Oracle database, depending on
# the file name.
# Also checks for /u01/oradata/INSTANCE/cloned flag file
# and if it exists run a level0 and remove the flag file.
#
# syntax
#  rman_level0.sh INSTANCENAME
#  rman_level1.sh INSTANCENAME
# run as the oracle OS user or another user in the dba group.
#
# make sure instance name is provided and valid
HOME=/home/oracle
HOSTNAME=UVIDBP01
USER=oracle
ORACLE_BASE=/u01/app/oracle
ORACLE_HOME=/u01/app/oracle/product/12.1.0/dbhome_1
PATH=/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/home/oracle/.local/bin:/home/oracle/bin:/u01/app/oracle/product/12.1.0/dbhome_1/bin
RDATE=`date '+%Y-%m-%d'`
export HOME PATH HOSTNAME USER ORACLE_BASE ORACLE_HOME

N=`basename $0`
inst=`echo $1 | tr '[a-z]' '[A-Z]'`
if [ "$inst" = "" ] ; then
   echo "$N - No instance name provided" 1>&2
   exit 1
   fi
if [ ! -d /u01/oradata/$inst ] ; then
   echo "$N - invalid instance $inst" 1>&2
   exit 1
   fi
# are we doing level 0 or level 1 or some other (wrong) name?
FILE=X
if [ $N = rman_level0.sh ] ; then
   LEVEL=0
   FILE=rman_level0.rcv
   echo "$N - running level 0 backup for $inst"
   fi
if [ $N = rman_level1.sh ] ; then
   LEVEL=1
   FILE=rman_level1.rcv
   echo "$N - running level 1 backup for $inst"
   if [ -f /u01/oradata/$inst/cloned ] ; then
      LEVEL=0
      FILE=rman_level0.rcv
      echo "$N - clone flag found, switching to level 0 backup for $inst"
      fi
   fi
if [ X$FILE = XX ] ; then
   echo "$N - must be named rman_level0.sh or rman_level1.sh" 1>&2
   exit 1
   fi
ORAENV_ASK=NO
ORACLE_SID=$inst
# echo $ORAENV_ASK $ORACLE_SID
. /usr/local/bin/oraenv
echo "rman level $LEVEL backup of $ORACLE_SID started at" `date`
rman  <<EOF1
spool log to /home/oracle/logs/${ORACLE_SID}_rman_level${LEVEL}_${RDATE}.log ;
@/u01/app/oracle/scripts/$FILE
EOF1
RC=$?
echo ' '
echo "Return code $RC from RMAN backup of $inst at" `date`
rm -f /u01/oradata/$inst/cloned
exit $RC
[oracle@UVIDBT01 bin]$ 
