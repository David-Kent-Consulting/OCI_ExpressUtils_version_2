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

parent_compartment_name         = "alpha1_test"
child_compartment_name          = "edu_comp"
region                          = "us-ashburn-1"
dr_region                       = "us-phoenix-1"

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
dr_storage_client = BlockstorageClient(config)

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

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# Get the source VM boot and block volume data, we start by getting the block volumes.
print("Fetching volume(s) data......\n")
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()

# Get the VM data but do not pass a VM instance name, we do not need it in this use case
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    ""
)
vm_instances.populate_instances()

def get_vm_vol_metadata(vm_instance):
    
    vm_vol_metadata = {
        
        "bootvol_attachments"    : "",     # holds bootvol attachment data
        "vol_attachments"        : "",     # holds vol attachment data
        "boot_volumes"           : "",     # holds boot vols that are attached to the VM
        "volumes"                : "",     # holds the vols that are attached to the VM
        
    }
    
    # get the boot and block volume attachments
    bootvol_attachments = get_boot_vol_attachments(
        compute_client,
        vm_instance.availability_domain,
        child_compartment.id,
        vm_instance.id
    )
    vol_attachments = get_block_vol_attachments(
        compute_client,
        vm_instance.availability_domain,
        child_compartment.id,
        vm_instance.id
    )

    # get the boot and block volumes
    boot_volumes = []
    for bva in bootvol_attachments:
        boot_volume = storage_client.get_boot_volume(
            boot_volume_id = bva.boot_volume_id
        ).data
        boot_volumes.append(boot_volume)
    volumes = []
    for bva in vol_attachments:
        volume = storage_client.get_volume(
            volume_id = bva.volume_id
        ).data
        volumes.append(volume)
    
    # populate the dictionary and return
    vm_vol_metadata["bootvol_attachments"]       = bootvol_attachments
    vm_vol_metadata["vol_attachments"]           = vol_attachments
    vm_vol_metadata["boot_volumes"]              = boot_volumes
    vm_vol_metadata["volumes"]                   = volumes
    
    return vm_vol_metadata
    
    
# end function get_vm_vol_metadata()

def get_region_backup_snaps(bv_client, vm_vol_metadata):
    
    regional_backups = {
        "all_boot_volume_backups"      : "",     # holds all boot volume backup snap data
        "all_volume_backups"           : ""      # holds all volume backup snap data
    }
    # get bootvol backups
    all_boot_volume_backups = []
    for bootvol in vm_vol_metadata["boot_volumes"]:
        boot_volume_backups = bv_client.list_boot_volume_backups(
            compartment_id = bootvol.compartment_id,
            boot_volume_id = bootvol.id
        ).data
        all_boot_volume_backups.append(boot_volume_backups)
    
    # get volume backups
    all_volume_backups = []
    for vol in vm_vol_metadata["volumes"]:
        volume_backups = bv_client.list_volume_backups(
            compartment_id = vol.compartment_id,
            volume_id = vol.id
        ).data
        all_volume_backups.append(volume_backups)
        
    # populate dictionary and return
    regional_backups["all_boot_volume_backups"]  = all_boot_volume_backups
    regional_backups["all_volume_backups"]       = all_volume_backups
    
    return regional_backups
    
# end function get_region_backup_snaps()

def get_vm_metadata(vm_instance):
    
    # dictonary object to hold VM metadata
    vm_metadata = {
    
        "vm_instance"            : "",     # holds vm instance resource data
        "vm_vol_metadata"        : "",     # holds all volume metadata
        "pri_region_backups"     : "",     # for each vol, we grab all snap backups in the primary region
        "pri_region_set_count"   : 0,      # will set if backups exists after we count all the sets
        "dr_region_backups"      : "",     # for each vol, we grab all snap backup replicas in the secondary region
        "is_backup_data"         : False,  # will be set to True if backup snaps are found in the primary region
        "inter_region_snaps_ok"  : "N/A"   # will be set to FalSe if a backup set in primary region != same in dr region
                                           # only 1 backup set need fail to trigger a false condition
    }
    
    
    vm_metadata["vm_instance"] = vm_instance
    
    # get volume metadata for this VM
    
    vm_metadata["vm_vol_metadata"] = get_vm_vol_metadata(vm_instance)
    
    # get primary region backups for all VM volumes
    
    vm_metadata["pri_region_backups"] = get_region_backup_snaps(
        storage_client,
        vm_metadata["vm_vol_metadata"]
    )
    
    # set is_backup_data to True if backup data exists in primary region for VM
    # We only have to check the first backup set of the first boot volume
    if (len(vm_metadata["pri_region_backups"]["all_boot_volume_backups"][0])) > 0:
        vm_metadata["is_backup_data"] = True
        vm_metadata["inter_region_snaps_ok"] = True # we'll set to False when we detect a problem

        # since we have backup data, we now must get the secondary region backups for all VM volumes
        vm_metadata["dr_region_backups"] = get_region_backup_snaps(
            dr_storage_client,
            vm_metadata["vm_vol_metadata"]
        )

        # now we have logic that compares the number of backups in each volume set to what's in the DR region
        # if a single set is != to its dr region, we set inter_region_snaps_ok to False
        counter = 0
        for primary_bootvol_backup_set in vm_metadata["pri_region_backups"]["all_boot_volume_backups"]:
            if (len(primary_bootvol_backup_set)) != len(vm_metadata["dr_region_backups"]["all_boot_volume_backups"][counter]):
                vm_metadata["inter_region_snaps_ok"] = False
            counter += 1
        
        counter = 0
        for primary_vol_backup_set in vm_metadata["pri_region_backups"]["all_volume_backups"]:
            if len(primary_vol_backup_set) != len(vm_metadata["dr_region_backups"]["all_volume_backups"][counter]):
                vm_metadata["inter_region_snaps_ok"] = False
            counter += 1
            
        # now we have to know the total number of backup sets in the primary region
        backup_set_count = 0
        for primary_bootvol_backup_set in vm_metadata["pri_region_backups"]["all_boot_volume_backups"]:
            backup_set_count = backup_set_count + len(primary_bootvol_backup_set)
        for primary_vol_backup_set in vm_metadata["pri_region_backups"]["all_volume_backups"]:
            backup_set_count = backup_set_count + len(primary_vol_backup_set)
        vm_metadata["pri_region_set_count"] = backup_set_count
    

    return vm_metadata

# end function get_vm_metadata()

def get_compartment_vm_metata_data(vm_instances):
    
    # This utility will eat memory, make sure we have at least 2Gb free for each iteration
    test_free_mem_2gb()
    
    all_vm_metadata = []
    for vm_instance in vm_instances:
        vm_metadata = get_vm_metadata(vm_instance)
        all_vm_metadata.append(vm_metadata)
    
    return all_vm_metadata

# end function get_compartment_vm_metata_data()

all_vm_metadata = get_compartment_vm_metata_data(vm_instances.return_all_instances())

header = [
    "COMPARTMENT",
    "VM",
    "BACKUP ENABLED(True/False)",
    "NUMBER OF BACKUP SETS",
    "INTER-REGION BACKUP STATUS"
]
data_rows = []

for vm_metadata in all_vm_metadata:
    if vm_metadata["inter_region_snaps_ok"] == True:
        status = "GOOD"
    elif vm_metadata["inter_region_snaps_ok"] == False:
        status = "NEEDS ATTENTION"
    else:
        status = "NOT ENABLED"
    data_row = [
        child_compartment_name,
        vm_metadata["vm_instance"].display_name,
        vm_metadata["is_backup_data"],
        vm_metadata["pri_region_set_count"],
        status   
    ]
    data_rows.append(data_row)
    
print(tabulate(data_rows, headers = header, tablefmt = "grid"))