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
from time import sleep

# required DKC modules
from lib.general import copywrite
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
from lib.compute import get_vm_instance_response
from lib.compute import update_instance_name

# required OCI modules
from oci.config import from_file
from oci import wait_until
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations

# required OCI decorators
from oci.core.models import UpdateInstanceDetails

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-UpdateVmName.py : Usage\n\n" +
        "Oci-UpdateVmName.py [parent compartment] [child compartment] [vm name] [new vm name] [region] [--force]\n\n" +
        "Use case example 1 changes the VM instance name from KENTBAST01 to KENTBASP01 for the specified virtual machine with no user prompt:\n" +
        "\tOci-UpdateVmName.py admin_comp tst_comp KENTBAST01 KENTBASP01  --force\n" +
        "Omit the --force option if you wish to be prompted prior to updating the change.\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
new_virtual_machine_name        = sys.argv[4]
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

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client = ComputeClient(config) # builds the compute client method, required to manage compute resources
compute_composite_client = ComputeClientCompositeOperations(compute_client)
#network_client = VirtualNetworkClient(config) # builds the network client, required to manage network resources


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
    "VM instance " + virtual_machine_name + " not found within compartment " + child_compartment_name + " within region " + region
)

# check for duplicates
for VM in vm_instances.instance_list:
    if VM.display_name == new_virtual_machine_name:
        print("VM instance {} already present in compartment {} within region {}.\n".format(
            virtual_machine_name,
            child_compartment_name,
            region
        ))
        print("Duplicate names are not permitted.\n\n")
        raise RuntimeWarning("WARNING! Duplicate VM instance names are not permitted.")

# run through the logic
results = None
if len(sys.argv) == 6:
    warning_beep(6)
    print("Enter YES to proceed with renaming VM instance {} to {}, or any other key to abort.\n".format(
        virtual_machine_name,
        new_virtual_machine_name
    ))
    if "YES" == input():
        results = update_instance_name(
            compute_client,
            UpdateInstanceDetails,
            vm_instance.id,
            new_virtual_machine_name
        )
    else:
        print("Name change aborted at user request.\n")
        exit(0)
elif option == "--FORCE":
    results = update_instance_name(
        compute_client,
        UpdateInstanceDetails,
        vm_instance.id,
        new_virtual_machine_name
    )
else:
    print(
        "\n\nINVALID OPTION! - The only valid option is --force\n" +
        "Please try again.\n\n"
    )
    raise RuntimeWarning("INVALID OPTION")

if results is None:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
else:
    print("VM instance name changed in OCI. This has no impact on the operating system name of the instance.\n\n")
    sleep(5)
    print(results)

