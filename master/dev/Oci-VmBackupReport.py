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
from datetime import datetime
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
from lib.backups import GetBackupPolicies
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

##########################################################################################################
#                                               functions                                                #
##########################################################################################################
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
    # ignore the IDE reported bogus sequence errors on vm_data, the code runs
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
    
    # This utility will eat memory, make sure we have at least 2Gb free between each iteration
    if not test_free_mem_2gb():
        raise RuntimeError("EXCEPTION! INSUFFICIENT MEMORY")
    
    all_vm_metadata = []
    if vm_instances is None:
        return None
    else:
        for vm_instance in vm_instances:
            vm_metadata = get_vm_metadata(vm_instance)
            all_vm_metadata.append(vm_metadata)
    
    return all_vm_metadata

# end function get_compartment_vm_metata_data()

##########################################################################################################
#                                               end functions                                            #
##########################################################################################################

if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "Oci-VmBackupReport.py : Usage\n\n" +
        "Oci-VmBackupReport.py [parent compartment] [child compartment] [VM instance]\n" +
        "[primary region] [secondary region] [optional argument]\n\n" +
        "Use case example 1 reports the status of all VM instance backups in the specified compartment:\n" +
        "\tOci-VmBackupReport.py acad_comp math_comp list_all_backups 'us-ashburn-1' 'us-phoenix-1'\n" +
        "Use case example 2 reports the status of backups for the specified VM instance:\n" +
        "\tOci-VmBackupReport.py acad_comp math_comp algebrap01 'us-ashburn-1' 'us-phoenix-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! Usage error")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_machine_name                = sys.argv[3]
region                              = sys.argv[4]
dr_region                           = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = None # required for logic

if option != "--JSON":
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
correct_region = False
for rg in regions:
    if rg.name == dr_region:
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
config["region"] = dr_region # reset to DR region for pulling DR backup copies
dr_storage_client = BlockstorageClient(config) # dr region instance

if option != "--JSON":
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
if option != "--JSON":
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

if option != "--JSON":
    print("Fetching and validating backup data......\n")

if virtual_machine_name.upper() == "LIST_ALL_BACKUPS" and len(sys.argv) == 6:

    all_vm_metadata = get_compartment_vm_metata_data(vm_instances.return_all_instances())
    header = [
        "COMPARTMENT",
        "VM",
        "BACKUP ENABLED(True/False)",
        "NUMBER OF BACKUP SETS",
        "INTER-REGION SYNCHRONIZATION STATUS"
    ]
    data_rows = []

    if all_vm_metadata is None:
        warning_beep(2)
        print("\n\nNo VM instances found within compartment {} in region {}".format(
            child_compartment_name,
            region
        ))
        raise RuntimeWarning("WARNING! NO VM INSTANCES FOUND.")
    else:
        for vm_metadata in all_vm_metadata:
            if vm_metadata["inter_region_snaps_ok"] == True:
                status = "HEALTHY"
            elif vm_metadata["inter_region_snaps_ok"] == False:
                status = "NOT FULLY SYNCHRONIZED"
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

elif len(sys.argv) == 6:

    # make sure we have at least 2GB free RAM prior to running this
    if not test_free_mem_2gb():
        raise RuntimeError("EXCEPTION! INSUFFICIENT MEMORY")
    vm_instance_found = False
    for vm_instance in vm_instances.return_all_instances():
        if vm_instance.display_name == virtual_machine_name:
            vm_instance_found = True
            vm_metadata = get_vm_metadata(vm_instance)
            secondary_boot_volume_backups = dr_storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id
            ).data
            secondary_volume_backups = dr_storage_client.list_volume_backups(
                compartment_id = child_compartment.id
            ).data
            
            header = [
                "COMPARTMENT",
                "VM",
                "BACKUP NAME",
                "SYNCHORNIZATION STATE",
                "PROTECTED VOLUME",
                "DATE",
                "LIFECYCLE STATE",
                "PRIMARY REGION",
                "SECONDARY REGION",
            ]
            data_rows = []

            # we need to get bootvol backups first since OCI has separate APIs for boot vols & vols
            for backup_set in vm_metadata["pri_region_backups"]["all_boot_volume_backups"]:
                # We have a backup set for each volume, and we much parse through each set
                for backup_item in backup_set:
                    # get bootvol data so we can dereference the disk volume being protected
                    boot_volume = storage_client.get_boot_volume(
                        boot_volume_id = backup_item.boot_volume_id
                    ).data

                    # parse through the bootvol replicase for the item
                    backup_replica_status = "NOT REPLICATED"
                    # print(backup_item.boot_volume_id)
                    # print(backup_item.display_name)
                    for boot_vol_replica in secondary_boot_volume_backups:
                        if boot_vol_replica.boot_volume_id == backup_item.boot_volume_id:
                            # print("an item was found")
                            if backup_item.display_name in boot_vol_replica.display_name:
                                # print("item found")
                                if backup_item.lifecycle_state in ["TERMINATED", "TERMINATING"]:
                                    backup_replica_status = "EXPIRED BACKUP"
                                elif backup_item.lifecycle_state == boot_vol_replica.lifecycle_state:
                                    backup_replica_status = "SYNCHRONIZED"
                                elif backup_item.lifecycle_state == "CREATING":
                                    backup_replica_status = "PENDING"
                                elif backup_item.lifecycle_state == "FAULTY":
                                    backup_replica_status = "PRIMARY BACKUP FAULTY"
                                elif backup_item.lifecycle_state == "AVAILABLE" and boot_vol_replica.lifecycle_state == "CREATING":
                                    backup_replica_status = "IN PROGRESS"
                                elif boot_vol_replica.lifecycle_state not in ["AVAILABLE", "TERMINATED", "TERMINATING"]:
                                    backup_replica_status = "FAULTY"
                                # print(backup_replica_status)

                    '''
                    We get the secondary region's backups, then parse down the complete set to find the item.
                    We then compare the item's state to the primary region's item state, if they match, we
                    consider the set as synchornized, if not, we report as unsynchornized.
                    '''
                    data_row = [
                        child_compartment_name,
                        virtual_machine_name,
                        backup_item.display_name,
                        backup_replica_status,
                        boot_volume.display_name,
                        backup_item.time_created.ctime(),
                        backup_item.lifecycle_state,
                        region,
                        dr_region
                    ]
                    data_rows.append(data_row)
            
            # repeat the same for volumes as we did above
            for backup_set in vm_metadata["pri_region_backups"]["all_volume_backups"]:
                for backup_item in backup_set:
                    volume = storage_client.get_volume(
                        volume_id = backup_item.volume_id
                    ).data
                    # parse through the volumes now like above with the boot volumes
                    backup_replica_status = "NOT REPLICATED"
                    for vol_replica in secondary_volume_backups:
                        if vol_replica.volume_id == backup_item.volume_id:
                            # print("volumes match")
                            if backup_item.display_name in vol_replica.display_name:
                                # print("item match")
                                if backup_item.lifecycle_state in ["TERMINATED", "TERMINATING"]:
                                    backup_replica_status = "EXPIRED BACKUP"
                                elif backup_item.lifecycle_state == vol_replica.lifecycle_state:
                                    backup_replica_status = "SYNCHRONIZED"
                                elif backup_item.lifecycle_state == "CREATING":
                                    backup_replica_status = "PENDING"
                                elif backup_item.lifecycle_state == "FAULTY":
                                    backup_replica_status = "PRIMARY BACKUP FAULTY"
                                elif backup_item.lifecycle_state == "AVAILABLE" and vol_replica.lifecycle_state == "CREATING":
                                    backup_replica_status = "IN PROGRESS"
                                elif vol_replica.lifecycle_state not in ["AVAILABLE", "TERMINATED", "TERMINATING"]:
                                    backup_replica_status = "FAULTY"
                    # print(backup_replica_status)

                    data_row = [
                        child_compartment_name,
                        virtual_machine_name,
                        backup_item.display_name,
                        backup_replica_status,
                        volume.display_name,
                        backup_item.time_created.ctime(),
                        backup_item.lifecycle_state,
                        region,
                        dr_region
                    ]
                    data_rows.append(data_row)

            print(tabulate(data_rows, headers = header, tablefmt = "grid"))


    if not vm_instance_found:
        warning_beep(2)
        print("\n\nVM instance {} not found within compartment {} in region {}\n\n".format(
            virtual_machine_name,
            child_compartment_name,
            region
        ))
        raise RuntimeWarning("WARNING! VM INSTANCE NOT FOUND")


elif option == "--FAILED-BACKUPS":

    pass

elif option == "--JSON":

    vm_instance_found = False
    for vm_instance in vm_instances.return_all_instances():
        if vm_instance.display_name == virtual_machine_name:
            vm_instance_found = True
            vm_metadata = get_vm_metadata(vm_instance)
            print(vm_metadata)
    
    if not vm_instance_found:
        warning_beep(2)
        print("\n\nVM instance {} not found within compartment {} in region {}\n\n".format(
            virtual_machine_name,
            child_compartment_name,
            region
        ))
        raise RuntimeWarning("WARNING! VM INSTANCE NOT FOUND")

else:
    print(
        "\n\nINVALID OPTION! Valid options are:\n\n" +
        "\t--json\t\t\tReport all backup sets for the specified VM in JSON format and supress other output\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )
    raise RuntimeWarning("USAGE ERROR!")


