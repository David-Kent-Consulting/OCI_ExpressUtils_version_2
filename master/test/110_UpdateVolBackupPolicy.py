#!/Users/henrywojteczko/bin/python
# Modify the above entry to point to the client's python3 virtual environment prior to execution

'''
# Copyright 2019 – 2020 David Kent Consulting, Inc.
# All Rights Reserved.
# 
# NOTICE:  All information contained herein is, and remains
# the property of David Kent Consulting, Inc.; David Kent Cloud Solutions, Inc.;
# and its affiliates (The Company). The intellectual and technical concepts contained
# herein are proprietary to The Company and may be covered by U.S. and Foreign Patents,
# patents in process, and are protected by trade secret or copyright law.
# Dissemination of this information or reproduction of this material
# is strictly forbidden unless prior written permission is obtained
# from The Company.
#
# This file is subject to the terms and conditions defined in
# file 'LICENSE.txt', which is part of this source code package.
'''
import oci
import os.path
import sys

if len(sys.argv) != 4: # ARGS PLUS COMMAND
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')


policy_id           = sys.argv[1]
start_time          = int(sys.argv[2])*3600
retention           = int(sys.argv[3])*3600*24
# Removed 25-June-2020 hankwojteczko@davidkentconsulting.com per Oracle SR 3-23212688391
# Issues persist in OCI cross-region backups, constrained to not more than 10 concurrent copies per
# region per tenancy.
#cross_region_backup = str.lower(sys.argv[4])            # API must pass value in lower case or region copy does not happen

# functions
def ApplyScheduleToBackupPolicy(block_storage_client, myPolicy_id, myStart_time, myRetention):
    backup_schedules = []

    volume_backup_schedule = oci.core.models.VolumeBackupSchedule(
        backup_type = "INCREMENTAL",
        hour_of_day = 1,
        time_zone = "REGIONAL_DATA_CENTER_TIME",
        retention_seconds = myRetention,
        period = "ONE_DAY",
        offset_seconds = myStart_time+10800
    )
    backup_schedules.append(volume_backup_schedule)

    volume_backup_schedule = oci.core.models.VolumeBackupSchedule(
        backup_type = "FULL",
        hour_of_day = 1,
        time_zone = "REGIONAL_DATA_CENTER_TIME",
        retention_seconds = myRetention,
        period = "ONE_WEEK",
        offset_seconds = myStart_time
    )
    backup_schedules.append(volume_backup_schedule)

    volume_backup_policy_details = oci.core.models.UpdateVolumeBackupPolicyDetails(
        schedules = backup_schedules,
#        destination_region = cross_region_backup
    )


    results = block_storage_client.update_volume_backup_policy(
        policy_id = myPolicy_id,
        update_volume_backup_policy_details = volume_backup_policy_details
    ).data
    print(results)
# end function ApplyScheduleToBackupPolicy

# Default config file and profile
config = oci.config.from_file()

block_storage_client = oci.core.BlockstorageClient(config)


ApplyScheduleToBackupPolicy(block_storage_client, policy_id, start_time, retention)
