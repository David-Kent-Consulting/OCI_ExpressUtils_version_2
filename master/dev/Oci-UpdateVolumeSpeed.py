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

# required built-in modules
import os.path
import sys
from time import sleep

# required DKC modules
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import is_int
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.volumes import GetVolumes
from lib.volumes import update_volume_performance

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import BlockstorageClientCompositeOperations
from oci.core import ComputeClient

from oci.core.models import UpdateVolumeDetails

if len(sys.argv) < 7 or len(sys.argv) > 8:
    print(
        "\n\nOci-UpdateVolumeSpeed.py : Usage\n\n" +
        "Oci-UpdateVolumeSpeed.py [parent compartment] [child compartment] [instance] [volume name] [speed rating LOW/BALANCED/HIGH] [region] [optional argument]\n" +
        "Use case example sets the volume speed rate to high performance:\n" +
        "\tOci-UpdateVolumeSpeed.py admin_comp dbs_comp kentrmanp01 kentrmanp01_datavol_0 HIGH 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Usage Error")


parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
volume_name                     = sys.argv[4]
volume_speed                    = sys.argv[5].upper()
if volume_speed not in ["LOW", "BALANCED", "HIGH"]:
    raise RuntimeWarning("INVALID CHOICE! - Valid choices for volume speed are LOW, BALANCED, or HIGH.")
region                          = sys.argv[6]
if len(sys.argv) == 8:
    option = sys.argv[7].upper()
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

config["region"]                    = region # Must set the cloud region
identity_client                     = IdentityClient(config) # builds the identity client method, required to manage compartments
storage_client                      = BlockstorageClient(config)
storage_composite_client            = BlockstorageClientCompositeOperations(storage_client)
compute_client                      = ComputeClient(config)

print("\n\nFetching tenant resource data, please wait......\n")
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

# get VM instance data
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()
error_trap_resource_not_found(
    vm_instance,
    "VM instance " + virtual_machine_name + " not found within compartment " + child_compartment_name + " within region " + region
)
# make sure the VM instance is not running. This is not fool proof, but we try to limit the weakness in the API.
# The API will allow for changing a volume performane rate while the instance is running, which we do not like.
# We'll have to revisit this in a later code version to account for all conditions.
if vm_instance.lifecycle_state != "STOPPED":
    raise RuntimeWarning("WARNING! VM instance must be in a STOPPED state for changing the volume's speed.")
# get the availability domains
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# check to see if the volume does not exists and if so, raise exception
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id
)
volumes.populate_block_volumes()
volume = volumes.return_block_volume_by_name(volume_name)
error_trap_resource_not_found(
    volume,
    "Volume " + volume_name + " already present in compartment " + child_compartment_name + " within region " + region
)

# run through the logic

if len(sys.argv) == 7:
    warning_beep(6)
    print("Enter YES to proceed with speed change to {} for volume {} or any other key to abort.\n".format(
        volume_speed,
        volume_name
    ))
    if "YES" != input():
        print("\n\nVolume speed change aborted per user request.\n\n")
        exit(0)
elif len(sys.argv) == 8 and option != "--FORCE":
    raise RuntimeWarning("INVALID OPTION! - The only valid option is --force")

# proceed to change the volume's performance rate
print("Changing the speed rate of volume {}. Please wait......\n".format(volume_name))
volume_update_request_result = update_volume_performance(
    storage_composite_client,
    UpdateVolumeDetails,
    volume.id,
    volume_speed
)
if volume_update_request_result.data.lifecycle_state == "AVAILABLE":
    print("Volume speed rate change completed successfully. Please examine the results below.\n".format(
        volume_name
    ))
    sleep(5)
    print(volume_update_request_result.data)
else:
    print("Oops, something went wrong. Please check the results below.\n")
    sleep(5)
    print(volume_update_request_result.data)
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")


