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
import platform
import resource
import sys
from tabulate import tabulate
from time import sleep


# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import test_free_mem_2gb
from lib.general import warning_beep
from lib.backups import add_volume_to_backup_policy
from lib.backups import GetBackupPolicies
from lib.backups import delete_volume_backup_policy
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeAttachment

# required DKC modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient

# functions




parent_compartment_name      = "alpha1_test"
child_compartment_name       = "edu_comp"
region                       = "us-ashburn-1"
dr_region                    = "us-phoenix-1"

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
    if rg.name == dr_region:
        correct_region = True
if not correct_region:
    print("\n\nWARNING! - Disaster Recovery Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client = ComputeClient(config)
storage_client = BlockstorageClient(config)
config["region"] = dr_region # reset to DR region for pulling DR backup copies
dr_storage_client = BlockstorageClient

print("\n\nFetching and verifying tenant resource data, please wait......\n")
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

# Get the VM data
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    ""
)
vm_instances.populate_instances()
if vm_instances.return_all_instances() is None:
    print("There are no VM instances in compartment {} within region {}".format(
        child_compartment_name,
        region
    ))
    raise RuntimeWarning("NO VM INSTANCES IN COMPARTMENT")

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# We will now create a dictionary object that will hold the data we are tracking.
# This will be completely populated by each volume we have found volumes for. The

vm_data = {
    "vm_instance"              : "",    # will hold the full VM instance resource data
    "volume_name"              : "",    # will hold a string value representing the volume name
    "volume_type"              : "",    # will be string value of either BOOT_VOLUME or VOLUME
    "backup_policy_assignment" : "",    # will hold a string value representing the backup policy assignment
    "primary_region_backups"   : "",    # will hold all primary region backup resource data
    "dr_region_backups"        : "",    # will hold all dr region backup resource data
    "backup_data_present"      : "",    # will be set to True if backup data is found for the volume, False if not
    "backup_consistency_check" : "",    # will be set to True if backup counts are consistent, false if inconsistent, or left as null if backup_data_present is False
}

print((test_free_mem_2gb()))