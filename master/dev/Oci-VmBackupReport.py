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
from lib.general import test_free_mem_1gb
from lib.general import warning_beep
from lib.backups import GetBackupPolicies
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeAttachment

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient

##########################################################################################################
#                                               functions                                                #
##########################################################################################################

def get_compartment_backup_data():
    
    # get all vm and volume data

    all_vm_backup_data = []
    for vm_instance in vm_instances.return_all_instances():
        vm_backup_data = {
            "vm_name"                  : "",
            "vm_id"                    : "",
            "boot_volumes"             : "",
            "boot_vol_backups_enabled" : False,
            "pri_boot_vol_backups"     : "",
            "pri_bootvol_set_count"    : 0,
            "dr_boot_vol_backups"      : "",
            "dr_bootvol_set_count"     : 0,
            "volumes"                  : "",
            "vol_backups_enabled"      : False,
            "pri_vol_backups"          : "",
            "pri_vol_set_count"        : 0,
            "dr_vol_backups"           : "",
            "dr_vol_set_count"         : 0
        }
    
        bootvol_attachments = get_boot_vol_attachments(
            compute_client,
            vm_instance.availability_domain,
            child_compartment.id,
            vm_instance.id
        )
        boot_volumes = []
        for bva in bootvol_attachments:
            boot_volume = storage_client.get_boot_volume(
                boot_volume_id = bva.boot_volume_id
            ).data
            boot_volumes.append(boot_volume)

    
        vol_attachments = get_block_vol_attachments(
            compute_client,
            vm_instance.availability_domain,
            child_compartment.id,
            vm_instance.id
        )
        volumes = []
        for bva in vol_attachments:
            volume = storage_client.get_volume(
                volume_id = bva.volume_id
            ).data
            volumes.append(volume)
    
        # get the primary region backups for each boot volume
        # we ignore anything that is TERMINATING or TERMINATED
        # we do this to conserve RAM and to avoid OCI buffer
        # overflow issues.
        pri_boot_vol_backups = []
        for boot_volume in boot_volumes:
            backup_resource = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = boot_volume.id,
                lifecycle_state = "AVAILABLE"
            ).data
            pri_boot_vol_backups.append(backup_resource)
            
        for boot_volume in boot_volumes:
            backup_resource = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = boot_volume.id,
                lifecycle_state = "CREATING"
            ).data
            pri_boot_vol_backups.append(backup_resource)
        for boot_volume in boot_volumes:
            backup_resource = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = boot_volume.id,
                lifecycle_state = "FAULTY"
            ).data
            pri_boot_vol_backups.append(backup_resource)
        # now count what you have and set the values for boot_vol_backups_enabled &
        # backup set counts for each section
        counter = 0
        for set in pri_boot_vol_backups:
            counter += len(set)
        if counter != 0:
            vm_backup_data["boot_vol_backups_enabled"] = True
            vm_backup_data["pri_bootvol_set_count"]    = counter

        ####################################################################################
        # ONLY DO THE FOLLOWING IF BOOTVOLUME BACKUPS ARE DETECTED AS ENABLED
        ####################################################################################
        
            # now get the secondary region backups for each boot volume
            dr_boot_vol_backups = []
            for boot_volume in boot_volumes:
                backup_resource = dr_storage_client.list_boot_volume_backups(
                    compartment_id = child_compartment.id,
                    boot_volume_id = boot_volume.id,
                    lifecycle_state = "AVAILABLE"
                ).data
                dr_boot_vol_backups.append(backup_resource)
            for boot_volume in boot_volumes:
                backup_resource = dr_storage_client.list_boot_volume_backups(
                    compartment_id = child_compartment.id,
                    boot_volume_id = boot_volume.id,
                    lifecycle_state = "CREATING"
                ).data
                dr_boot_vol_backups.append(backup_resource)
            for boot_volume in boot_volumes:
                backup_resource = dr_storage_client.list_boot_volume_backups(
                    compartment_id = child_compartment.id,
                    boot_volume_id = boot_volume.id,
                    lifecycle_state = "FAULTY"
                ).data
                dr_boot_vol_backups.append(backup_resource)
            counter = 0
            for set in dr_boot_vol_backups:
                counter += len(set)
            vm_backup_data["dr_bootvol_set_count"] = counter
        
            # get the backups only if data volumes are attached to the VM just as in the above
            pri_vol_backups = []
            dr_vol_backups  = []
            if len(volumes) > 0:
        
                for volume in volumes:
                    backup_resource = storage_client.list_volume_backups(
                        compartment_id = child_compartment.id,
                        volume_id = volume.id,
                        lifecycle_state = "AVAILABLE"
                    ).data
                    pri_vol_backups.append(backup_resource)
                for volume in volumes:
                    backup_resource = storage_client.list_volume_backups(
                        compartment_id = child_compartment.id,
                        volume_id = volume.id,
                        lifecycle_state = "CREATING"
                    ).data
                    pri_vol_backups.append(backup_resource)
                for volume in volumes:
                    backup_resource = storage_client.list_volume_backups(
                        compartment_id = child_compartment.id,
                        volume_id = volume.id,
                        lifecycle_state = "FAULTY"
                    ).data
                    pri_vol_backups.append(backup_resource)
                    
                # See if we have volume backups
                counter = 0
                for set in pri_vol_backups:
                    counter += len(set)
                if counter != 0:
                    vm_backup_data["vol_backups_enabled"] = True
                    vm_backup_data["pri_vol_set_count"] = counter
                    
                    ####################################################################################
                    # ONLY DO THE FOLLOWING IF VOLUME BACKUPS ARE DETECTED AS ENABLED
                    ####################################################################################
            
                    for volume in volumes:
                        backup_resource = dr_storage_client.list_volume_backups(
                            compartment_id = child_compartment.id,
                            volume_id = volume.id,
                            lifecycle_state = "AVAILABLE"
                        ).data
                        dr_vol_backups.append(backup_resource)
                    for volume in volumes:
                        backup_resource = dr_storage_client.list_volume_backups(
                            compartment_id = child_compartment.id,
                            volume_id = volume.id,
                            lifecycle_state = "CREATING"
                        ).data
                        dr_vol_backups.append(backup_resource)
                    for volume in volumes:
                        backup_resource = dr_storage_client.list_volume_backups(
                            compartment_id = child_compartment.id,
                            volume_id = volume.id,
                            lifecycle_state = "FAULTY"
                        ).data
                        dr_vol_backups.append(backup_resource)
                    
                    counter = 0
                    for set in dr_vol_backups:
                        counter += len(set)
                    vm_backup_data["dr_vol_set_count"] = counter
    
        vm_backup_data["vm_name"]               = vm_instance.display_name
        vm_backup_data["vm_id"]                 = vm_instance.id
        vm_backup_data["boot_volumes"]          = boot_volumes
        vm_backup_data["pri_boot_vol_backups"]  = pri_boot_vol_backups

        vm_backup_data["dr_boot_vol_backups"]   = dr_boot_vol_backups
        vm_backup_data["volumes"]               = volumes
        vm_backup_data["pri_vol_backups"]       = pri_vol_backups
        vm_backup_data["pri_vol_backups"]       = dr_vol_backups

    
        all_vm_backup_data.append(vm_backup_data)
    
    return all_vm_backup_data

# end function get_compartment_backup_data()

def report_compartment_backups():
    
    data_rows = []
    header = [
        "COMPARTMENT",
        "VM",
        "BACKUP\nENABLED",
        "NUMBER OF\nBACKUP SETS",
        "INTER-REGION\nSYNCHRONIZATION\nSTATUS"
    ]
    for vm_backup_data in all_vm_backup_data:
        if vm_backup_data["boot_vol_backups_enabled"]:
            if vm_backup_data["dr_bootvol_set_count"] != 0:
                if vm_backup_data["pri_bootvol_set_count"] != vm_backup_data["dr_bootvol_set_count"]:
                    syncd_state = "NOT FULLY SYNCHORNIZED"
                else:
                    if vm_backup_data["vol_backups_enabled"]:
                        if vm_backup_data["pri_vol_set_count"] != vm_backup_data["dr_vol_set_count"]:
                            syncd_state = "NOT FULLY SYNCHRONIZED"
                        else:
                            syncd_state = "SYNCHRONIZATION ENABLED"
                    else:
                        syncd_state = "SYNCHRONIZATION ENABLED"
            else:
                syncd_state = "NOT ENABLED"
            
            # add up all the sets
            set_count = vm_backup_data["pri_bootvol_set_count"] + \
                vm_backup_data["pri_vol_set_count"]
            
            data_row = [
                child_compartment_name,
                vm_backup_data["vm_name"],
                True,
                set_count,
                syncd_state
            ]
            data_rows.append(data_row)
                
        else:
            data_row = [
                child_compartment_name,
                vm_backup_data["vm_name"],
                False,
                "N/A",
                "N/A"
            ]
            data_rows.append(data_row)

    print(tabulate(data_rows, headers = header, tablefmt = "grid"))
# end function report_compartment_backups()

def report_vm_backup(virtual_machine_name,
                    output_option):
    
    data_rows = []
    for vm_instance in vm_instances.instance_list:

        if vm_instance.display_name == virtual_machine_name:
            
            header = [
                "COMPARTMENT",
                "VM",
                "BACKUP ID",
                "SYNCHRONIZATION\nSTATE",
                "PROTECTED\nVOLUME",
                "DATE",
                "LIFECYCLE\nSTATE",
                "PRIMARY\nREGION",
                "SECONDARY\nREGION"
            ]
            
            bootvol_attachments = get_boot_vol_attachments(
                compute_client,
                vm_instance.availability_domain,
                child_compartment.id,
                vm_instance.id
            )
            boot_volumes = []
            for bva in bootvol_attachments:
                boot_volume = storage_client.get_boot_volume(
                    boot_volume_id = bva.boot_volume_id
                ).data
                boot_volumes.append(boot_volume)
            
            vol_attachments = get_block_vol_attachments(
                compute_client,
                vm_instance.availability_domain,
                child_compartment.id,
                vm_instance.id
            )
            volumes = []
            for bva in vol_attachments:
                volume = storage_client.get_volume(
                    volume_id = bva.volume_id
                ).data
                volumes.append(volume)
                
            pri_boot_vol_backups = []
            dr_boot_vol_backups = []
            ###############################################################
            # BOOT VOLUMES FIRST
            ###############################################################
            
            # We constrain our search into small parts to avert a membuf overflow from OCI
            for boot_volume in boot_volumes:
                backup_resource = storage_client.list_boot_volume_backups(
                    compartment_id = child_compartment.id,
                    boot_volume_id = boot_volume.id,
                    lifecycle_state = "AVAILABLE"
                ).data
                pri_boot_vol_backups.append(backup_resource)
            for boot_volume in boot_volumes:
                backup_resource = storage_client.list_boot_volume_backups(
                    compartment_id = child_compartment.id,
                    boot_volume_id = boot_volume.id,
                    lifecycle_state = "CREATING"
                ).data
                pri_boot_vol_backups.append(backup_resource)
            for boot_volume in boot_volumes:
                backup_resource = storage_client.list_boot_volume_backups(
                    compartment_id = child_compartment.id,
                    boot_volume_id = boot_volume.id,
                    lifecycle_state = "FAULTY"
                ).data
                pri_boot_vol_backups.append(backup_resource)
            counter = 0
            for bk_set in pri_boot_vol_backups:
                counter += len(bk_set)
            if counter > 0:
                for boot_volume in boot_volumes:
                    backup_resource = dr_storage_client.list_boot_volume_backups(
                        compartment_id = child_compartment.id,
                        boot_volume_id = boot_volume.id,
                        lifecycle_state = "AVAILABLE"
                    ).data
                    dr_boot_vol_backups.append(backup_resource)
                    backup_resource = dr_storage_client.list_boot_volume_backups(
                        compartment_id = child_compartment.id,
                        boot_volume_id = boot_volume.id,
                        lifecycle_state = "CREATING"
                    ).data
                    dr_boot_vol_backups.append(backup_resource)
                    backup_resource = dr_storage_client.list_boot_volume_backups(
                        compartment_id = child_compartment.id,
                        boot_volume_id = boot_volume.id,
                        lifecycle_state = "FAULTY"
                    ).data
                    dr_boot_vol_backups.append(backup_resource)
            
            for bk_set in pri_boot_vol_backups:
                for bk_item in bk_set:
                    syncd_state = "NOT SYNCHRONIZED"
                    for dr_set in dr_boot_vol_backups:
                        for drbk_item in dr_set:
                            if drbk_item.source_boot_volume_backup_id == bk_item.id:
                                if drbk_item.lifecycle_state == "AVAILABLE":
                                    syncd_state = "SYNCHRONIZED"
                                elif drbk_item.lifecycle_state == "CREATING":
                                    syncd_state = "IN\nPROGRESS"
                                elif drbk_item == "FAULTY":
                                    syncd_state = "FAULTY"
                                
                    data_row = [
                        child_compartment_name,
                        virtual_machine_name,
                        bk_item.id,
                        syncd_state,
                        boot_volume.display_name,
                        bk_item.time_created.ctime(),
                        bk_item.lifecycle_state,
                        region,
                        dr_region
                    ]
                    data_rows.append(data_row)
                    
            ###############################################################
            # VOLUMES NEXT
            ###############################################################
            for volume in volumes:
                pri_vol_backups = []
                dr_vol_backups = []
                backup_resource = storage_client.list_volume_backups(
                    compartment_id = child_compartment.id,
                    volume_id = volume.id,
                    lifecycle_state = "AVAILABLE"
                ).data
                pri_vol_backups.append(backup_resource)
                backup_resource = storage_client.list_volume_backups(
                    compartment_id = child_compartment.id,
                    volume_id = volume.id,
                    lifecycle_state = "CREATING"
                ).data
                pri_vol_backups.append(backup_resource)
                backup_resource = storage_client.list_volume_backups(
                    compartment_id = child_compartment.id,
                    volume_id = volume.id,
                    lifecycle_state = "FAULTY"
                ).data
                pri_vol_backups.append(backup_resource)
                
                counter = 0
                for bk_set in pri_vol_backups:
                    counter += len(bk_set)

                if counter > 0:
                    for volume in volumes:
                        backup_resource = dr_storage_client.list_volume_backups(
                            compartment_id = child_compartment.id,
                            volume_id = volume.id,
                            lifecycle_state = "AVAILABLE"
                        ).data
                        dr_vol_backups.append(backup_resource)
                    for volume in volumes:
                        backup_resource = dr_storage_client.list_volume_backups(
                            compartment_id = child_compartment.id,
                            volume_id = volume.id,
                            lifecycle_state = "CREATING"
                        ).data
                        dr_vol_backups.append(backup_resource)
                    for volume in volumes:
                        backup_resource = dr_storage_client.list_volume_backups(
                            compartment_id = child_compartment.id,
                            volume_id = volume.id,
                            lifecycle_state = "FAULTY"
                        ).data
                        dr_vol_backups.append(backup_resource)
            
                for bk_set in pri_vol_backups:
                    for bk_item in bk_set:
                        syncd_state = "NOT SYNCHORNIZED"
                        for dr_set in dr_vol_backups:
                            for drbk_item in dr_set:
                                if drbk_item.source_volume_backup_id == bk_item.id:
                                    if drbk_item.lifecycle_state == "AVAILABLE":
                                        syncd_state = "SYNCHRONIZED"
                                    elif drbk_item.lifecycle_state == "CREATING":
                                        syncd_state = "IN\nPROGRESS"
                                    elif drbk_item.lifecycle_state == "FAULTY":
                                        syncd_state = "FAULTY"
                        data_row = [
                            child_compartment_name,
                            virtual_machine_name,
                            bk_item.id,
                            syncd_state,
                            volume.display_name,
                            bk_item.time_created.ctime(),
                            bk_item.lifecycle_state,
                            region,
                            dr_region
                        ]
                        data_rows.append(data_row)
                
            if output_option == "--JSON":
                print(pri_boot_vol_backups)
                print(dr_boot_vol_backups)
                print(pri_vol_backups)
                print(dr_vol_backups)
            else:
                pass
                print(tabulate(data_rows, headers = header, tablefmt = "grid"))

# end function report_vm_backup()

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
# make sure we have 1GB free RAM before starting
test_free_mem_1gb()


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

    all_vm_backup_data = get_compartment_backup_data()
    report_compartment_backups()

elif len(sys.argv) == 6:

    report_vm_backup(virtual_machine_name, "")


elif option == "--FAILED-BACKUPS":
    # future release
    pass

elif option == "--JSON":

    report_vm_backup(virtual_machine_name, option)

else:
    print(
        "\n\nINVALID OPTION! Valid options are:\n\n" +
        "\t--json\t\t\tReport all backup sets for the specified VM in JSON format and supress other output\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )
    raise RuntimeWarning("USAGE ERROR!")


