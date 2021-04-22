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
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import is_int
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.backups import GetBackupPolicies
from lib.backups import add_backup_schedule
from lib.backups import check_schedule

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core.models import UpdateVolumeBackupPolicyDetails
from oci.core.models import VolumeBackupSchedule

copywrite()
sleep(2)
if len(sys.argv) != 11:
    print(
        "\n\nOci-AddBackupPolicySchedule.py : Usage:\n\n" +
        "Oci-AddBackupPolicySchedule.py [parent compartment] [child compartment] [policy name]\n" +
        "[backup type (FULL/INCREMENTAL) [day of week] [month of year] [start hour (0-23)]\n" +
        "[backup frequency (DAILY/WEEKLY/MONTHLY/YEARLY)] [days to retain] [region]\n\n"
        "Use case example 1 adds the specified FULL schedule to the policy to start on\n" +
        "Sunday at 01:00 regional data center time\n" +
        "\tOci-AddBackupPolicySchedule.py admin_comp bak_comp kentdmzt01_backup FULL SUNDAY \\ \n" +
        "\t  JANUARY 1 WEEKLY 31 'us-ashburn-1'\n\n"+
        "Use case example 2 adds the specified INCREMENTAL schedule to the policy to start on\n" +
        "Monday at 03:00 regional data center time and run each day\n" +
        "\tOci-AddBackupPolicySchedule.py admin_comp bak_comp kentdmzt01_backup INCREMENTAL MONDAY \\ \n" +
        "\t  JANUARY 3 DAILY 31 'us-ashburn-1'\n\n" +
        "Use case example 3 adds the specified FULL annual backup schedule to the policy to start on\n" +
        "the first day of December and retains the data for 2 years\n" +
        "\tOci-AddBackupPolicySchedule.py admin_comp bak_comp kentdmzt01_backup FULL SUNDAY \\ \n" +
        "\t  DECEMBER 3 YEARLY 730 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! Usage error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
backup_policy_name              = sys.argv[3]

backup_type                     = sys.argv[4].upper()
if backup_type not in ["FULL", "INCREMENTAL"]:
    raise RuntimeWarning("INVALID VALUE! Backup type must be FULL or INCREMENTAL")

day_of_week                     = sys.argv[5].upper()
month_of_year                   = sys.argv[6].upper()

if not is_int(sys.argv[7]):
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! - Start time must be an integer between 0 and 23")
start_time                     = int(sys.argv[7])
if start_time not in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]:
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! - Start time must be an integer between 0 and 23")

if sys.argv[8].upper() == "DAILY":
    backup_job_frequency = "ONE_DAY"
elif sys.argv[8].upper() == "WEEKLY":
    backup_job_frequency = "ONE_WEEK"
elif sys.argv[8].upper() == "MONTHLY":
    backup_job_frequency = "ONE_MONTH"
elif sys.argv[8] == "YEARLY":
    backup_job_frequency = "ONE_YEAR"
else:
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! Valid values for backup frequency are DAILY, WEEKLY, MONTHLY, or YEARLY")

if not is_int(sys.argv[9]) or int(sys.argv[9]) < 1:
    warning_beep(1)
    raise RuntimeWarning("INVALID VALUE! - Days to retain must be an integer of at least 1")
retention_in_days               = int(sys.argv[9])

region                          = sys.argv[10]


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
    "Backup policy " + backup_policy_name + " not present within compartment " + child_compartment_name + " within region " + region
)

# Make sure the schedule does not exist prior to adding it to the backup policy
if check_schedule(
    backup_policy,
    backup_type,
    backup_job_frequency,
    start_time):
    warning_beep(1)
    raise RuntimeWarning("WARNING! Backup schedule already exists")
    
# Add the schedule to the backup policy
results = add_backup_schedule(
    storage_client,
    UpdateVolumeBackupPolicyDetails,
    VolumeBackupSchedule,
    backup_policy,
    backup_type,
    day_of_week,
    month_of_year,
    start_time,
    backup_job_frequency,
    retention_in_days
)

print("Backup schedule addition successful. Please inspect the results below.\n")
sleep(5)
print(results)

