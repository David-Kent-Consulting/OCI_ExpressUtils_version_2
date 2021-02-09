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
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.compute import get_block_vol_attachments
from lib.volumes import delete_volume_attachment
from lib.volumes import delete_volume
from lib.volumes import GetVolumeAttachment
from lib.volumes import GetVolumes

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import BlockstorageClientCompositeOperations

if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-DetachVolume.py : Usage\n\n" +
        "Oci-DetachVolume.py [parent compartment] [child compartment] [VM instance name] [volume name] [region] [optional argument]\n" +
        "Use case example detaches the volume from the specified VM instance:\n" +
        "\tOci-DetachVolume.py admin_comp dbs_comp kentrmanp01 kentrmanp01_datavol_0 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Usage Error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
volume_name                     = sys.argv[4]
region                          = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
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
compute_composite_client            = ComputeClientCompositeOperations(compute_client)

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
print("\n\nFetching tenant resource data, please wait......\n")
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()
error_trap_resource_not_found(
    vm_instance,
    "VM instance " + virtual_machine_name + " not found in compartment " + child_compartment_name + " within region " + region
)
# instance must be running to attach
if vm_instance.lifecycle_state == "RUNNING":
    raise RuntimeWarning("WARNING! VM Instance must not be running to detach a volume.")

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
    "Volume " + volume_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# check to make sure the volume is not already attached to the VM instance
volume_attachments = GetVolumeAttachment(
    compute_client,
    child_compartment.id
)
volume_attachments.populate_volume_attachments()
volume_attachment = volume_attachments.return_vol_attachment(volume.id)
error_trap_resource_not_found(
    volume_attachment,
    "Volume " + volume_name + " already attached to VM instance " + virtual_machine_name
)

# run through the logic
if len(sys.argv) == 6:
    warning_beep(6)
    print("Enter YES to proceed to detach volume {} from VM instance {}, or any other key to abort.\n".format(
        volume_name,
        virtual_machine_name
    ))
    if "YES" != input():
        print("Volume detachment aborted per user request.\n")
        exit(0)
elif option != "--FORCE":
    warning_beep(1)
    raise RuntimeWarning("INVALID OPTION! The only valid option is --force")

# proceed with the detachment.
print("\nDetaching volume {} from VM instance {}. Please wait......\n".format(
    volume_name,
    virtual_machine_name
))

detachment_request_results = delete_volume_attachment(
    compute_composite_client,
    volume_attachment.id
)
if detachment_request_results.data.lifecycle_state != "DETACHED":
    warning_beep(1)
    print("\n\nWARNING! - Volume detachment failed, please review the results below\n")
    print(detachment_request_results.data)
else:
    print("\nVolume detachment successful, please inspect the results below.\n")
    sleep(10)
    print(detachment_request_results.data)
