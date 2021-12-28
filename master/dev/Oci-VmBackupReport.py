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

    all_vm_backup_data = [] # will hold a list of the dictionary objects defined below
    for vm_instance in vm_instances.return_all_instances():
        # this is the dictionary object
        vm_backup_data = {
            "vm_name"                  : "",
            "vm_id"                    : "",
            "boot_vol_backups_enabled" : False,   # will set to true if bootvol backup objects are found
            "vol_backups_enabled"      : False,   # will set to true if vol backup objects are found
            "boot_volumes"             : "",      # will contain a list of boot volumes
#             "boot_vol_backups"     : "",          # will contain a list of boot volume backups if found
            "volumes"                  : ""      # will contain a list of volumes if found
#             "vol_backups"          : ""           # will contain a list of volume backups if found
        }
        
        # we have to know the bootvol attachments to get to boot vols for the VM
        bootvol_attachments = get_boot_vol_attachments(
            compute_client,
            vm_instance.availability_domain,
            child_compartment.id,
            vm_instance.id
        )
        
        # now we get the boot volumes
        boot_volumes = []
        for bva in bootvol_attachments:
            boot_volume = storage_client.get_boot_volume(
                boot_volume_id = bva.boot_volume_id
            ).data
            boot_volumes.append(boot_volume)
    
        # we have to know the vol attachments to get any volumes
        vol_attachments = get_block_vol_attachments(
            compute_client,
            vm_instance.availability_domain,
            child_compartment.id,
            vm_instance.id
        )
        
        # Now we get the volumes, if any
        volumes = []
        for bva in vol_attachments:
            volume = storage_client.get_volume(
                volume_id = bva.volume_id
            ).data
            volumes.append(volume)
            
        vm_backup_data["vm_name"]            = vm_instance.display_name
        vm_backup_data["vm_id"]              = vm_instance.id
        vm_backup_data["boot_volumes"]       = boot_volumes
        vm_backup_data["volumes"]            = volumes
    
        '''
        In this section we will walk down each bootvol and pull any backup data by its status. The statuses
        we look for are AVAILABLE, CREATING, TERMINATED, TERMINATING, and FAULTY. This is done so we avoid 
        exceeding the page legnth in the API call. Each set of results are appended to boot_volumes, which 
        is later added to the dictionary object vm_backup_data.
        '''
        boot_vol_backups = []
        for bv in boot_volumes:
            backups = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = bv.id,
                lifecycle_state = "AVAILABLE"
            ).data
            # now append each backup set to bool_vol_backups
            for bk in backups:
                boot_vol_backups.append(bk)
            '''
            Repeat this operand now for each lifecycle that we must collect data about.
            '''
            backups = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = bv.id,
                lifecycle_state = "CREATING"
            ).data
            for bk in backups:
                boot_vol_backups.append(bk)
            
            backups = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = bv.id,
                lifecycle_state = "FAULTY"
            ).data
            for bk in backups:
                boot_vol_backups.append(bk)
                
            backups = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = bv.id,
                lifecycle_state = "TERMINATED"
            ).data
            for bk in backups:
                boot_vol_backups.append(bk)
                
            backups = storage_client.list_boot_volume_backups(
                compartment_id = child_compartment.id,
                boot_volume_id = bv.id,
                lifecycle_state = "TERMINATING"
            ).data
            for bk in backups:
                boot_vol_backups.append(bk)
                
        '''
        Now we will repeat the same operand for volume backups
        '''
        vol_backups = []
        for v in volumes:
            backups = storage_client.list_volume_backups(
                compartment_id = child_compartment.id,
                volume_id = v.id,
                lifecycle_state = "AVAILABLE"
            ).data
            for bk in backups:
                vol_backups.append(bk)
                
            backups = storage_client.list_volume_backups(
                compartment_id = child_compartment.id,
                volume_id = v.id,
                lifecycle_state = "CREATING"
            ).data
            
            for bk in backups:
                vol_backups.append(bk)

            backups = storage_client.list_volume_backups(
                compartment_id = child_compartment.id,
                volume_id = v.id,
                lifecycle_state = "FAULTY"
            ).data
            for bk in backups:
                vol_backups.append(bk)

            backups = storage_client.list_volume_backups(
                compartment_id = child_compartment.id,
                volume_id = v.id,
                lifecycle_state = "TERMINATED"
            ).data
            for bk in backups:
                vol_backups.append(bk)

                
            backups = storage_client.list_volume_backups(
                compartment_id = child_compartment.id,
                volume_id = v.id,
                lifecycle_state = "TERMINATING"
            ).data
            for bk in backups:
                vol_backups.append(bk)
                
        '''
        The dictionary object boot_vol_backups must now have boot_vol_backups and vol_backups appended to it.
        Set the values for boot_vol_backups_enabled and vol_backups_enabled
        '''
        vm_backup_data["boot_volume_backups"] = boot_vol_backups
        vm_backup_data["vol_backups"]         = vol_backups
        
        if len(boot_vol_backups) > 0:
            vm_backup_data["boot_vol_backups_enabled"] = True
        if len(vol_backups) > 0:
            vm_backup_data["vol_backups_enabled"] = True
        
        
        
        '''
        The very last action is to append all_vm_backups with this dictionary object, and then to return it
        to the calling code block
        '''
        all_vm_backup_data.append(vm_backup_data)
    
    
    '''
    Each dictionary object vm_backup_data contains the VM instance, block volumes, and any backups if found. We
    also have written to the object True for any backup types we have found. Each object is appended to
    all_vm_backup_data.
    '''
    
    
    return all_vm_backup_data


# end function get_compartment_backup_data()

##########################################################################################################
#                                             end functions                                              #
##########################################################################################################

copywrite()
sleep(2)
if not test_free_mem_1gb():
    raise RuntimeError("INSUFFICIENT RAM, 1GB FREE RAM REQUIRED\n\n")


if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "Oci-VmBackupReport.py : Usage\n\n" +
        "Oci-VmBackupRepoprt.py [parent compartment] [child compartment] [virtual machine] [region] [option]\n\n" +
        "Use case example below lists the backup summary for all virtual machines in the specified compartment:\n" +
        "\tOci-VmBackupReport.py admin_comp dbs_comp list_all_backups 'us-ashburn' --summary-only\n\n" +
        "Use case example below lists detailed backups for all virtual machines in the specified compartment:\n" +
        "\tOci-VmBackupReport admin_comp dbs_comp list_all_backups 'us-ashburn-1'\n\n" +
        "Use case example below lists detailed backup for the specified virtual machine:\n" +
        "\tOci-VmBackupReport.py admin_comp dbs_comp kentrmanp01 'us-ashburn-1'\n\n" +
        "Use case example below lists all backup data for the specified virtual machine in JSON format\n" +
        "\tOci-VmBackupReport.py admin_comp dbs_comp kentrmanp01 'us-ashburn-1' --json\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("INVALID USAGE\n\n")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_machine_name                = sys.argv[3]
region                              = sys.argv[4]

if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None
if option is not None and option not in ["--SUMMARY-ONLY", "--JSON"]:
    raise RuntimeWarning("INVALID OPTIONS, VALID OPTIONS ARE --SUMMARY-ONLY OR --JSON")

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

    config["region"] = region # dictionary object
identity_client = IdentityClient(config) # identity instance
compute_client = ComputeClient(config) # compute instance
storage_client = BlockstorageClient(config) # storage instance primary region

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

# Get the VM data but do not pass a VM instance name, we do not need it in this use case
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()

if virtual_machine_name.upper() != "LIST_ALL_BACKUPS":
    virtual_machine = vm_instances.return_instance()
    
    error_trap_resource_not_found(
        virtual_machine_name,
        "Virtual machine {} not found in compartment {} within region {}\n".format(
            virtual_machine_name,
            child_compartment_name,
            region
        )
    )

print("Fetching compartment backup data. Please wait......\n")
all_compartment_backup_data = get_compartment_backup_data()

if virtual_machine_name.upper() != "LIST_ALL_BACKUPS":
    if option is None:
        for vm in all_compartment_backup_data:
            if vm["vm_name"] == virtual_machine_name:
                if not vm["boot_vol_backups_enabled"]:
                    print("\nBackups for virtual machine {} are not enabled\n\n".format(virtual_machine_name))
                    exit (0)
                elif not vm["vol_backups_enabled"]:
                    print("\nData volume backups are not enabled or no data volumes exist for virtual machine {}\n\n".format(virtual_machine_name))
            else:
                header = [
                    "VIRTUAL\nMACHINE",
                    "BACKUP\nTYPE",
                    "BACKUP\nDATE",
                    "STATUS",
                    "BACKUP\n\OBJECT\nOCID"
                ]
                backup_objects = []
                for bk in vm["boot_volume_backups"]:
                    backup_object = [
                        virtual_machine_name,
                        "BOOT VOLUME",
                        bk.time_created.ctime(),
                        bk.lifecycle_state,
                        bk.id
                    ]
                    backup_objects.append(backup_object)
                
                for bk in vm["vol_backups"]:
                    backup_object = [
                        virtual_machine_name,
                        "DATA VOLUME",
                        bk.time_created.ctime(),
                        bk.lifecycle_state,
                        bk.id
                    ]
                    backup_objects.append(backup_object)
                
                print(tabulate(backup_objects, headers = header, tablefmt = "grid"))
    elif option == "--SUMMARY-ONLY": # do the summary report

        for vm in all_compartment_backup_data:
            if vm["vm_name"] == virtual_machine_name:
                successful_backups = 0
                backups_in_progress = 0
                faulty_backups = 0
                terminated_backups = 0
                for bk in vm["boot_volume_backups"]:
                    if bk.lifecycle_state == "AVAILABLE":
                        successful_backups += 1
                    elif bk.lifecycle_state == "CREATING":
                        backups_in_progress += 1
                    elif bk.lifecycle_state == "FAULTY":
                        faulty_backups += 1
                    elif bk.lifecycle_state == "TERMINATED" or bk.lifecycle_state == "TERMINATING":
                        terminated_backups += 1
                for bk in vm["vol_backups"]:
                    if bk.lifecycle_state == "AVAILABLE":
                        successful_backups += 1
                    elif bk.lifecycle_state == "CREATING":
                        backups_in_progress += 1
                    elif bk.lifecycle_state == "FAULTY":
                        faulty_backups += 1
                    elif bk.lifecycle_state == "TERMINATED" or bk.lifecycle_state == "TERMINATING":
                        terminated_backups += 1
        print("sucessful {}\n".format(successful_backups))
        print("in progress {}\n".format(backups_in_progress))
        print("faulty {}\n".format(faulty_backups))
        print("terminated {}\n".format(terminated_backups))




