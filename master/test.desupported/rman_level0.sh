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

rman  <<EOF1
spool log to /home/oracle/logs/${ORACLE_SID}_rman_level${LEVEL}_${RDATE}.log ;
connect target /
run
{
   allocate channel ch_disk_1 device type disk maxpiecesize = 4000M;
   allocate channel ch_disk_2 device type disk maxpiecesize = 4000M;
   allocate channel ch_disk_3 device type disk maxpiecesize = 4000M;
   configure controlfile autobackup off;
   configure retention policy to recovery window of 31 days;
   CONFIGURE COMPRESSION ALGORITHM 'HIGH';
   BACKUP incremental level 0 cumulative DATABASE
      diskratio=0
      tag='level1_database_backup'
      format='/u04/RMAN/%d/%d_databasefile_%T_%s_%p_%t'
      ;
   sql 'alter system archive log current';
   backup
      archivelog FROM TIME 'SYSDATE-2'
      format='/u04/RMAN/%d/%d_archivelog_%T_%s_%p_%t'
      tag='archivelogs'
      ;
   backup
      current controlfile
       format='/u04/RMAN/%d/%d_controlfile_%T_%s_%p_%t'
       tag='controlfile'
      ;
}
crosscheck backup;
crosscheck copy;
delete obsolete;
list backup;
exit
EOF1

# groom any orphined files 1 time per week
/usr/bin/find  /u04/RMAN/${ORACLE_SID} -type f -name '*' -mtime +45 -print | xargs rm -rf