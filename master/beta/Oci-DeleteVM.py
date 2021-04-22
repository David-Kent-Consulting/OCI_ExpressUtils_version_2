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
# required OCI modules
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
from lib.general import return_availability_domain
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import terminate_instance
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeAttachment

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import BlockstorageClient
from oci.core import BlockstorageClientCompositeOperations

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-DeleteVM.py : Usage\n\n" +
        "Oci-DeleteVM.py [parent compartment] [child compartment] [vm name]\n" +
        "[preserve disks (True/False)] [region] [optional argument]\n\n" +
        "Use case Example 1 deletes the specified virtual machine within the specified compartment and region\n" +
        "and deletes the VM's disk volumes:\n" +
        "\tOci-DeleteVM.py admin_comp tst_comp DKCESMT01 False 'us-ashburn-1'\n" +
        "Use case example 2 deletes the specified virtual machine within the specified compartment and region\n" +
        "and preserves the disk volumes:\n" +
        "\tOci-DeleteVM.py admin_comp tst_comp DKCESMT01 True 'us-ashburn-1'\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
preserve_disks                  = sys.argv[4].upper()
if preserve_disks == "TRUE":
    preserve_disks = True
elif preserve_disks == "FALSE":
    preserve_disks = False
else:
    raise RuntimeWarning("INVALID VALUE! - preserve disks must be true or false.")
region                          = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = [] # required for logic to work

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
compute_client = ComputeClient(config) # builds the network client method, required to manage network resources
compute_composite_client = ComputeClientCompositeOperations(compute_client) # build composite operations methond
storage_client = BlockstorageClient(config)
storage_composite_client = BlockstorageClientCompositeOperations(storage_client)

# get the parent compartment data
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
    "Virtual machine instance " + virtual_machine_name + " not found in compartment " + \
        child_compartment_name + " in region " + region
)

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# get the VM volume attachments
volume_attachments = GetVolumeAttachment(
    compute_client,
    child_compartment.id
)
vm_volumes = []
volume_attachments.populate_volume_attachments()

if volume_attachments.return_all_vol_attachments() is not None:
    for va in volume_attachments.return_all_vol_attachments():
        if va.instance_id == vm_instance.id:
            volume_attachment = va
            # get the block volumes for subsequent termination
            volumes = GetVolumes(
                storage_client,
                availability_domains,
                child_compartment.id)
            volumes.populate_block_volumes()
            volume = volumes.return_block_volume(va.volume_id)
            vm_volumes.append(volume)

# run through the logic

# first look and see if the VM instance is in a running state, if so, abort
if vm_instance.lifecycle_state != "STOPPED":
    print("\n\nVM instance {} in compartment {} within region {} is not in a stopped state\n".format(
        virtual_machine_name,
        child_compartment_name,
        region
    ))
    print(
        "This tool will not permit the deletion of a VM while not in a stopped state.\n" +
        "Please stop the VM instance and run this utility again.\n\n"
    )
    raise RuntimeWarning("WARNING! - Unable to submit VM instance delete request")
if len(sys.argv) == 6:
    warning_beep(6)
    print("\n\nEnter YES to delete VM instance {} from compartment {} within region {} or any other key to abort".format(
        virtual_machine_name,
        child_compartment_name,
        region
    ))
    if "YES" != input():
        print("\n\nVM instance delete request aborted by user.\n\n")
        exit(0)
elif option != "--FORCE":
    warning_beep(1)
    raise RuntimeWarning("INVALID OPTION! - The only valid option is --force")


# delete the VM instance and print the results
print("\n\nDelete request for VM {} submitted, please wait......".format(virtual_machine_name))
# compute client is required to terminate an instance and leave the OS disk in place.
delete_vm_response = terminate_instance(
    compute_client,
    compute_composite_client,
    vm_instance.id,
    preserve_disks
)

if delete_vm_response is None:
    raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
else:
    header = [
        "VM NAME",
        "LIFECYCLE\nSTATE",
        "COMPARTMENT",
        "REGION"
    ]
    print("\n\nVM successfully deleted. Please inspect the results below.\n")
    print(tabulate(
        [[
            virtual_machine_name,
            "TERMINATED or TERMINATING",
            child_compartment_name,
            region
        ]],
        headers = header,
        tablefmt = "simple"
    ))

    

    if not preserve_disks:
    
        if len(vm_volumes) > 0:
            print("Proceeding to delete disk volumes")
            for bv in vm_volumes:
                delete_volume_results = storage_composite_client.delete_volume_and_wait_for_state(
                    volume_id = bv.id,
                    wait_for_states = ["TERMINATED","FAULTY", "UNKNOWN_ENUM"]
                ).data
                if delete_volume_results.lifecycle_state != "TERMINATED":
                    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
                else:
                    print(tabulate([[
                        delete_volume_results.display_name,
                        delete_volume_results.lifecycle_state,
                        region
                    ]], headers = [
                        "VOLUME NAME",
                        "LIFECYCLE\nSTATE",
                        "REGION"
                    ],
                    tablefmt = "grid"))
        else:
            print("\nThis VM instance has no data disks to delete.\n\n")

    else:
        print(
            "\nThe VM's disk volumes have been left in place along with any\n" +
            "backup policy assignments. These must be manually removed this\n" +
            "point forward.\n\n"
        )

