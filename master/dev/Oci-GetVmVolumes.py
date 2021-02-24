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
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.compute import reboot_instance
from lib.vcns import GetVirtualCloudNetworks
from lib.volumes import attach_paravirtualized_volume
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeBackups


# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient


if len(sys.argv) <5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetVmVolumes.py : Usage\n\n" +
        "Oci-GetVmVolumes.py [parent compartment] [child compartment] [VM] [region] [optional argument]\n" +
        "Usage example lists the boot and data volumes for the specified VM instance:\n" +
        "\tOci-GetVmVolumes.py admin_comp bas_comp kentdmzt01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect usage")

# define global vars
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_machine_name                = sys.argv[3]
region                              = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None
    copywrite()
    sleep(2)

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
compute_client                      = ComputeClient(config)

if option == None: # supress output for JSON format
    print("\n\nGathering and validating tenancy resource data. Please wait......\n")
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

# get the source VM data
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

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# Get the source VM boot and block volume data, we start by getting the block volumes.
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()

# next we sort through the boot volume attachments and pull the boot vol attachments for the source VM
boot_vol_attachments = get_boot_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id
    )

# now we get the boot volumes for the souerce VM
boot_volumes = []
for boot_vol_attachment in boot_vol_attachments:
    boot_volume = volumes.return_boot_volume(boot_vol_attachment.boot_volume_id)
    boot_volumes.append(boot_volume)

# next we get the block volume attachments
block_vol_attachments = get_block_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id)

# finally we get the block volume data
block_volumes = []
for block_volume_attachment in block_vol_attachments:
    block_volume = volumes.return_block_volume(block_volume_attachment.volume_id)
    block_volumes.append(block_volume)

# print volume information
if len(sys.argv) == 5:
    header = [
        "VM NAME",
        "VOLUME TYPE",
        "VOLUME_NAME",
        "SIZE IN GBytes",
        "PERFORMANCE SETTING",
        "LIFECYCLE STATE"
    ]

    data_rows = []
    for bv in boot_volumes:
        # required to set human readable value for performance_setting
        if bv.vpus_per_gb == 0:
            performance_setting = "LOW"
        elif bv.vpus_per_gb == 10:
            performance_setting = "BALANCED"
        elif bv.vpus_per_gb == 20:
            performance_setting = "HIGH"
        data_row = [
            virtual_machine_name,
            "BOOT VOLUME",
            bv.display_name,
            bv.size_in_gbs,
            performance_setting,
            bv.lifecycle_state
        ]
        data_rows.append(data_row)
    
    for bv in block_volumes:
        if bv.vpus_per_gb == 0:
            performance_setting = "LOW"
        elif bv.vpus_per_gb == 10:
            performance_setting = "BALANCED"
        elif bv.vpus_per_gb == 20:
            performance_setting = "HIGH"
        data_row = [
            virtual_machine_name,
            "DATA VOLUME",
            bv.display_name,
            bv.size_in_gbs,
            performance_setting,
            bv.lifecycle_state
        ]
        data_rows.append(data_row)

    print(tabulate(data_rows, headers = header, tablefmt = "grid"))


elif option != "--JSON":
    warning_beep(1)
    raise RuntimeWarning("INVALID OPTION! - The only valid option is --json")
else:
    print(boot_volumes)
    print(block_volumes)