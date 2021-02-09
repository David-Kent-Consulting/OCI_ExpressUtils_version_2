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
import os.path
import sys
from time import sleep
# the following must be added to the python library with PIP and the path to anaconda must be appended to PYTHONPATH
# use caution when modifying the PYTHONPATH env var, test everything
from tabulate import tabulate


from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.backups import GetBackupPolicies
from lib.backups import delete_volume_backup_policy

from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core.models import CreateVolumeBackupPolicyDetails
from oci.core.models import UpdateVolumeBackupPolicyDetails

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetBackupPolicy.py : Usage:\n\n" +
        "Oci-GetBackupPolicy.py [parent compartment] [child compartment] [policy name] [region] [optional argument]\n\n" +
        "Use case example 1 lists all backup policies in the child compartment and lists them by name:\n" +
        "\tOci-GetBackupPolicy.py admin_comp bak_comp list_all_policies 'us-ashburn-1' --name\n\n" +
        "Use case example 2 lists the specified backup policy within the specified compartment:\n" +
        "\tOci-GetBackupPolicy.py admin_comp bak_comp kentdmzt01_backup 'us-ashburn-1\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! Usage error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
backup_policy_name              = sys.argv[3]
region                          = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
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
# error_trap_resource_not_found(
#     backup_policy,
#     "Backup policy " + backup_policy_name + " not present within compartment " + parent_compartment_name + " within region " + region
# )

# passwd to tabulate for printing schedules
col = ["POLICY_NAME", "BACKUP TYPE", "START TIME", "START DAY", "START MONTH", "DAYS TO RETAIN"]


# run through the logic
if len(sys.argv) == 5 and sys.argv[3].upper() == "LIST_ALL_POLICIES":
    for policy in backup_policies.return_all_volume_backup_policies():
        print(policy)
elif len(sys.argv) == 6 and sys.argv[3].upper() == "LIST_ALL_POLICIES" and option == "--NAME":
    print(
        "\n\nPOLICY NAME\n" +
        "==============================="
    )
    for policy in backup_policies.return_all_volume_backup_policies():
        print(policy.display_name)
elif len(sys.argv) == 6 and sys.argv[3].upper() == "LIST_ALL_POLICIES" and option == "--SCHEDULES":
    # We will use tabulate to print a properly formatted report
    data_rows = []
    for policy in backup_policies.return_all_volume_backup_policies():
        for schedule in policy.schedules:
            data_row = [policy.display_name, schedule.backup_type, schedule.hour_of_day, schedule.day_of_week, schedule.month, int(((schedule.retention_seconds/3600)/24))]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = col, tablefmt = "grid"))
else:
    error_trap_resource_not_found(
        backup_policy,
        "Backup policy " + backup_policy_name + " not present within compartment " + parent_compartment_name + " within region " + region
    )
    if len(sys.argv) == 5:
        print(backup_policy)
    elif option == "--OCID":
        print(backup_policy.id)
    elif option == "--NAME":
        print(backup_policy.display_name)
    elif option == "--SCHEDULES":
        data_rows = []
        for schedule in backup_policy.schedules:
            data_row = [backup_policy.display_name, schedule.backup_type, schedule.hour_of_day, schedule.day_of_week, schedule.month, int(((schedule.retention_seconds/3600)/24))]
            data_rows.append(data_row)
        print(tabulate(data_rows, headers = col, tablefmt = "grid"))
    else:
        print(
            "\n\nINVALID OPTION! Valid options are:\n"
            "\t--ocid\t\tPrints the OCID of the backup policy\n" +
            "\t--name\t\tPrints the name of the backup policy\n" +
            "\t--schedules\tPrints the policy(s) along with all defined schedules\n\n"
        )
        raise RuntimeWarning("INVALID OPTION!")