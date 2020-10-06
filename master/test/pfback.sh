#!/usr/bin/sh

# for these entries, login to the DBaaS, become the user oracle, and run the shell "env" command
HOME=/home/oracle
HOSTNAME=nwmsudbt02
LD_LIBRARY_PATH=/u01/app/oracle/product/19.0.0.0/dbhome_1/lib
LEVEL=1
ORACLE_BASE=/u01/app/oracle
ORACLE_HOME=/u01/app/oracle/product/19.0.0.0/dbhome_1
ORACLE_SID=FNHRCDB
ORACLE_UNQNAME=FNHRCDB_iad1qc
PATH=/usr/lib64/qt-3.3/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/u01/app/oracle/product/19.0.0.0/dbhome_1/bin:/home/oracle/.local/bin:/home/oracle/bin
RDATE=`date '+%Y-%m-%d'`
USER=oracle
export HOME LD_LIBRARY_PATH ORACLE_BASE ORACLE_HOME ORACLE_SID ORACLE_UNQNAME PATH USER

ORAENV_ASK=NO
# Make sure the SID is correct.
ORACLE_SID=FNHRCDB
# echo $ORAENV_ASK $ORACLE_SID
. /usr/local/bin/oraenv


PFLOC=/u04/RMAN/${ORACLE_SID}/init${ORACLE_SID}_${RDATE}.bak
export PFLOC
echo $PFLOC
ORAENV_ASK=NO
# echo $ORAENV_ASK $ORACLE_SID
. /usr/local/bin/oraenv
sqlplus <<EOF1
/ as sysdba
alter database backup controlfile to trace;
create pfile='$PFLOC' from spfile;
quit
EOF1
echo Backup done
echo
