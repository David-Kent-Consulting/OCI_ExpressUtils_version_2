#!/usr/bin/python3

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
The system env var PATHONPATH must be exported in the shell's profile. It must point to the location of the OCI
libraries. This is typically in the same directory structure that the OCI CLI installs to, such as
~./lib/oracle-cli/lib/python3.8/site-packages 

Below find a literal example:

export PYTHONPATH=/Users/henrywojteczko/lib/oracle-cli/lib/python3.8/site-packages

See https://docs.python.org/3/tutorial/modules.html#the-module-search-path and
https://stackoverflow.com/questions/54598292/python-modulenotfounderror-when-trying-to-import-module-from-imported-package

'''
# required system modules
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required OCI modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import is_int
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.backups import GetBackupPolicies
from lib.backups import delete_backup_schedule
from lib.backups import check_schedule

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient

# required OCI decorators
from oci.core.models import UpdateVolumeBackupPolicyDetails
from oci.core.models import VolumeBackupSchedule

copywrite()
sleep(2)
if len(sys.argv) < 8 or len(sys.argv) > 9:
    print(
        "\n\nOci-DeleteBackupPolicySchedule.py : Usage:\n\n" +
        "Oci-DeleteBackupPolicySchedule.py [parent compartment] [child compartment] [policy name]\n" +
        "[backup type (FULL/INCREMENTAL) [backup frequency (DAILY/WEEKLY/MONTHLY/YEARLY)] \n" +
        "[start hour (0-23)] [region] [optional argument]\n\n" +
        "Use case example deletes the specified FULL schedule from the policy\n" +
        "\tOci-DeleteBackupPolicySchedule.py admin_comp bak_comp kentdmzt01_backup FULL YEARLY 23 'us-ashburn-1'\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! Usage error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
backup_policy_name              = sys.argv[3]

backup_type                     = sys.argv[4].upper()
if backup_type not in ["FULL", "INCREMENTAL"]:
    raise RuntimeWarning("INVALID VALUE! Backup type must be FULL or INCREMENTAL")

if not is_int(sys.argv[6]):
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! - Start time must be an integer between 0 and 23")
start_time                     = int(sys.argv[6])
if start_time not in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]:
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! - Start time must be an integer between 0 and 23")

if sys.argv[5].upper() == "DAILY":
    backup_job_frequency = "ONE_DAY"
elif sys.argv[5].upper() == "WEEKLY":
    backup_job_frequency = "ONE_WEEK"
elif sys.argv[5].upper() == "MONTHLY":
    backup_job_frequency = "ONE_MONTH"
elif sys.argv[5] == "YEARLY":
    backup_job_frequency = "ONE_YEAR"
else:
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! Valid values for backup frequency are DAILY, WEEKLY, MONTHLY, or YEARLY")

region                          = sys.argv[7]

if len(sys.argv) == 9:
    option = sys.argv[8].upper
else:
    option = None # required for logic to work

# instiate the environment and validate that the specified region exists
config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config)
regions = get_regions(identity_client)
correct_region = False
for rg in regions:
    if rg.name == region:
        correct_region = True
if not correct_region:
    print("\n\nWARNING! - Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
storage_client = BlockstorageClient(config)

# Get the parent compartment
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Child compartment " + child_compartment_name + " not found within parent compartment " + parent_compartment_name
)

# See if the policy exists, and if so, raise exception
backup_policies = GetBackupPolicies(
    storage_client,
    child_compartment.id
)
backup_policies.populate_backup_policies()
backup_policy = backup_policies.return_volume_backup_policy(backup_policy_name)
error_trap_resource_not_found(
    backup_policy,
    "Backup policy " + backup_policy_name + " not present within compartment " + parent_compartment_name + " within region " + region
)

# the function returns None if the schedule is not found. Since there is no harm done,
# we choose to print that we have not found the schedule and exit normally.    
delete_backup_schedule_result = delete_backup_schedule(
    storage_client,
    UpdateVolumeBackupPolicyDetails,
    VolumeBackupSchedule,
    backup_policy,
    backup_type,
    backup_job_frequency,
    start_time
)

if delete_backup_schedule_result is not None:

    print(
        "\n\nBackup schedule successfully deleted from backup policy.\n" +
        "Here are the schedules that remain.\n"
        )

    header = [
        "SCHEDULE TYPE",
        "DAY OF MONTH",
        "DAY OF WEEK",
        "START TIME",
        "MONTH",
        "FREQUENCY",
        "BACKUP RETENTION IN DAYS"
    ]
    data_rows = []
    for schedule in delete_backup_schedule_result.schedules:
        data_row = [
            schedule.backup_type,
                schedule.day_of_month,
                schedule.day_of_week,
                schedule.hour_of_day,
                schedule.month,
                schedule.period,
                str((((schedule.retention_seconds)/60)/60)/24)
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    print("\n\nNo action taken, schedule is not present.\n")

