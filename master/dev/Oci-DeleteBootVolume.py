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

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.volumes import GetVolumes

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import BlockstorageClientCompositeOperations
from oci.core import ComputeClient

copywrite()
if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-DeleteBootVolume.py : Usage\n" +
        "Oci-DeleteBootVolume.py [parent compartment] [child compartment] [boot volume name] [region]\n\n" +
        "Use case example deletes the boot volume from the specified compartment without prompting the user:\n" +
        "\tOci-DeleteBootVolume.py acad_comp edu_comp 'EDUTEACHT01 (Boot Volume)' 'us-ashburn-1' --force\n" +
        "Remove the --force option to be prompted prior to deleting the boot volume.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
boot_volume_name                = sys.argv[3]
region                          = sys.argv[4]
if len(sys.argv) == 6:
    option                      = sys.argv[5].upper()
else:
    option                      = None

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

config["region"]                    = region # Must set the cloud region
identity_client                     = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client                      = ComputeClient(config)
storage_client                      = BlockstorageClient(config)
storage_composite_client            = BlockstorageClientCompositeOperations(storage_client)

print("\n\nFetching and validating tenancy reosurce data......")
# get the parent compartment data
parent_compartments                 = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment                  = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Child compartment " + child_compartment_name + " within parent compartment " + parent_compartment_name
)

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# Get the source VM boot and block volume data, we start by getting the block volumes.
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()
boot_volume = volumes.return_boot_volume_by_name(boot_volume_name)
error_trap_resource_not_found(
    boot_volume,
    "Boot volume " + boot_volume_name + " not found within compartment " + child_compartment_name + " within region " + region
)

'''
We must ensure that the volume is not in an attached state prior to attempting to delete it. We do so by:
    1) by availability domain, get the boot vol attachments and then parse through the list
       and append boot_vol_attachments
    2) parse each item  in boot_vol_attachments comparing bv.boot_volume_id to boot_volume_id
    3) If a match is found and the boot vol attachment's lifecycle state is not "DETACHED",
    raise a RuntimeError.
'''
boot_vol_attachments = []
for ad in availability_domains:
    list_boot_volume_attachments_response = compute_client.list_boot_volume_attachments(
        availability_domain = ad.name,
        compartment_id = child_compartment.id
    ).data
    for bva in list_boot_volume_attachments_response:
        boot_vol_attachments.append(bva)

for bva in boot_vol_attachments:
    if bva.boot_volume_id == boot_volume.id and bva.lifecycle_state != "DETACHED":
        warning_beep(2)
        # get VM resource data so we can retrieve the VM instance name
        vm_instance = compute_client.get_instance(instance_id = bva.instance_id).data
        print("Boot volume {} is currently attached to VM instance {} within\ncompartment {} in region {}\n".format(
            boot_volume_name,
            vm_instance.display_name,
            child_compartment_name,
            region
        ))
        print("Volumes must be in a detached state prior to deletion.\n\n")
        raise RuntimeError("EXCEPTION! VOLUME ATTACHED TO RESOURCE.")

# run through the logic
if len(sys.argv) == 5:
    warning_beep(6)
    print("Enter YES to proceed with deletion of boot volume {} or press enter to abort.".format(
        boot_volume_name
    ))
    if "YES" != input():
        print("\n\nBoot volume delete request aborted per user.\n\n")
        exit(0)
elif option != "--FORCE":
    warning_beep(1)
    raise RuntimeWarning("INVALID OPTION! The only valid option for this utility is --force")

# proceed to delete the volume and return results

print("Deleting volume......")
delete_boot_volume_response = storage_composite_client.delete_boot_volume_and_wait_for_state(
    boot_volume_id = boot_volume.id,
    wait_for_states = [
        "TERMINATED",
        "FAULTY",
        "UNKNOWN_ENUM_STATE"
    ]
).data
if delete_boot_volume_response.lifecycle_state != "TERMINATED":
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")

print("\n\nBoot volume deletion completed successfully.\n")
print(tabulate(
    [[
        child_compartment_name,
        boot_volume_name,
        delete_boot_volume_response.lifecycle_state,
        region
    ]],
    headers = [
        "COMPARTMENT",
        "BOOT VOLUME",
        "LIFECYCLE STATE",
        "REGION"
    ],
    tablefmt = "simple"
))
