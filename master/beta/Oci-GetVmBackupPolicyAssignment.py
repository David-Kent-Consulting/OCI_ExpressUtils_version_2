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


copywrite()
sleep(2)
if len(sys.argv) != 5:
    print(
        "\n\nOci-GetVmBackupPolicyAssignment.py : Usage:\n\n" +
        "Oci-GetVmBackupPolicyAssignment.py [parent compartment] [child compartment] [vm name] [region]\n\n" +
        "Use case example lists any backup policy assignments associated with the specified VM:\n" +
        "\tOci-GetVmBackupPolicyAssignment.py admin_comp bas_comp kentdmzt01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! Usage error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
region                          = sys.argv[4]

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
compute_client = ComputeClient(config)
storage_client = BlockstorageClient(config)

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
    virtual_machine_name
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()
error_trap_resource_not_found(
    vm_instance,
    "Virtual machine instance " + virtual_machine_name + " not found within compartment " + child_compartment_name + " in region " + region
)

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# get the boot and block volume attachments
boot_vol_attachments = get_boot_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id
    )

block_vol_attachments = get_block_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id)

# Get the source VM boot and block volume data, we start by getting the block volumes.
print("Fetching volume(s) data......\n")
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()


# # get the boot and block volumes that are attached to the VM instance
boot_volumes = []
for boot_vol_attachment in boot_vol_attachments:
    boot_volume = volumes.return_boot_volume(boot_vol_attachment.boot_volume_id)
    boot_volumes.append(boot_volume)

block_volumes = []
for block_volume_attachment in block_vol_attachments:
    block_volume = volumes.return_block_volume(block_volume_attachment.volume_id)
    block_volumes.append(block_volume)

# get the policy assignments for boot volumes
policy_assignments = []
for bv in boot_volumes:
    policy_assignment = storage_client.get_volume_backup_policy_asset_assignment(
        asset_id = bv.id
    ).data
    policy_assignments.append(policy_assignment)

# get the policy assignments for block volumes
for bv in block_volumes:
    policy_assignment = storage_client.get_volume_backup_policy_asset_assignment(
        asset_id = bv.id
    ).data
    policy_assignments.append(policy_assignment)

backup_policies = GetBackupPolicies(
    storage_client,
    child_compartment
)
backup_policies.populate_backup_policies()

# prepare the data for reporting options

data_rows = []
for bp in policy_assignments:
    if len(bp) == 0:
        warning_beep(2)
        print("\nVirtual machine {} in compartment {} is not assigned to a volume backup policy or".format(
            virtual_machine_name,
            child_compartment_name
        ))
        print(
            "not all of its volumes are assigned to a volume backup policy. You can add this VM to\n" +
            "a backup policy or fix an incomplete backup policy assignment by using\n"+
            "the Oci-AddVmToBackupPolicy.py utility\n\n"
        )
        exit(0)
        
    else:
        data_row = []

        # each bp is returned as a list, even though only 1 item will be in it.
        backup_policy = storage_client.get_volume_backup_policy(
            policy_id = bp[0].policy_id
        ).data
        for bv in boot_volumes:
            if bv.id == bp[0].asset_id:
                disk_type = "BOOT VOLUME"
                disk = bv
        for bv in block_volumes:
            if bv.id == bp[0].asset_id:
                disk_type = "DATA VOLUME"
                disk = bv
        data_row = [
            child_compartment_name,
            virtual_machine_name,
            bv.display_name,
            disk_type,
            backup_policy.display_name,
            region
        ]
        data_rows.append(data_row)


# print the results if data collection was successful
header = [
    "COMPARTMENT",
    "VM",
    "VOLUME",
    "VOLUME TYPE",
    "POLICY ASSIGNMENT",
    "REGION"
]
print("This VM is properly assigned to a backup policy. Please note the details below:\n\n")
print(tabulate(data_rows, headers = header, tablefmt = "grid"))

