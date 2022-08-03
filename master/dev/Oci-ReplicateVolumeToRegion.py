#!/usr/bin/python3

# Copyright 2019 – 2022 David Kent Consulting, Inc.
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

# system modules
from datetime import datetime
import os.path
import platform
import resource
import sys
from tabulate import tabulate
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import BlockstorageClientCompositeOperations
from oci.core import ComputeClient
from oci.core.models import CopyVolumeBackupDetails

copywrite()
sleep(2)
if len(sys.argv) != 6:
    print(
        "\n\nOci-ReplicateVolumeToRegion.py\n" +
        "Oci-ReplicateVolumeToRegion.py [parent compartment] [child compartment] [backup item ID] [source region] [destination region]\n\n" +
        "Use case example replicates the specified boot volume item to the specified destination region:\n" +
        "\tOci-ReplicateVolumeToRegion.py admin_comp dbs_comp \\\n" +
        "\t'ocid1.volumebackup.oc1.iad.abuwcljtslmyxmeakhrxbwwolo7b5vdi4e4jn5qwasti6atfhrzug4fl57wq' \\\n" +
        "\t'us-ashburn-1' 'us-phoenix-1'\n\n" +
        "CAUTION! OCI has limits on the number of concurrent inter-region backup replications. The default\n" +
        "limit is 5. You can request to increase this limit by opening an SR with Oracle Support.\n\n" +
        "CAUTION! Your tenancy must be subscribed to the destination region in order for the backup\n" + 
        "copy to successfully replicate.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
backup_item_id                      = sys.argv[3]
region                              = sys.argv[4]
destination_region                  = sys.argv[5]

# make sure the item is not a backup volume, then make sure it is a volume backup
if "bootvolumebackup" in backup_item_id:
    raise RuntimeWarning("WARNING! - Backup item is of boot volume type - must be of volume type")
elif "volumebackup" not in backup_item_id:
    raise RuntimeWarning("WARNING! - Item is not a type of volume backup!")

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
correct_region = False
for rg in regions:
    if rg.name == destination_region:
        correct_region = True
if not correct_region:
    print("\n\nWARNING! - Disaster Recovery Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

config["region"] = region # dictionary object
identity_client = IdentityClient(config) # identity instance
compute_client = ComputeClient(config) # compute instance
storage_client = BlockstorageClient(config) # storage instance primary region

print("\n\nFetching and validating tenancy resource data......")
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

backup_item = storage_client.get_volume_backup(
    volume_backup_id = backup_item_id
).data

print("Submitting volume backup replication request for item {} with the name {} in compartment {} from region {} to region {}\n\n".format(
    backup_item_id,
    backup_item.display_name,
    child_compartment_name,
    region,
    destination_region
))

replicate_backup_item_request_response = storage_client.copy_volume_backup(
    volume_backup_id = backup_item.id,
    copy_volume_backup_details = CopyVolumeBackupDetails(
        destination_region = destination_region,
        display_name = backup_item.display_name
    )
).data

print(
    "The backup item is replicating. This can take several minutes to several hours depending\n" +
    "on the size of the volume. Please inspect the details below.\n\n"
    )
header = [
    "COMPARTMENT",
    "BACKUP ITEM ID",
    "LIFECYCLE\nSTATUS",
    "SOURCE\nREGION",
    "DESTINATION\nREGION"
]
print(tabulate([[
    child_compartment_name,
    replicate_backup_item_request_response.id,
    replicate_backup_item_request_response.lifecycle_state,
    region,
    destination_region
]], headers = header, tablefmt = "simple"))

