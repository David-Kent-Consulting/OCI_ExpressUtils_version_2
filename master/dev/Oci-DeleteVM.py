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
import os.path
import sys
from time import sleep
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import warning_beep
from lib.general import return_availability_domain
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.compute import terminate_instance

from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-DeleteVM.py : Usage\n\n" +
        "Oci-DeleteVM.py [parent compartment] [child compartment] [vm name] [region] [optional argument]\n\n" +
        "Use case deletes the specified virtual machine within the specified compartment and region:\n" +
        "\tOci-DeleteVM.py admin_comp tst_comp DKCESMT01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
region                          = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = [] # required for logic to work

# instiate the environment
config = from_file() # gets ~./.oci/config and reads to the object
config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client = ComputeClient(config) # builds the network client method, required to manage network resources
compute_composite_client = ComputeClientCompositeOperations(compute_client) # build composite operations methond

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

# run through the logic
if len(sys.argv) == 6:
    if option == "--FORCE":
        print("Delete request for VM instance {} has been submitted. Please wait......\n".format(
            virtual_machine_name
        ))
        results = terminate_instance(
            compute_composite_client,
            vm_instance.id
        )
        if results is None:
            raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
        else:
            print("VM instance and OS {} terminated from compartment {} within region {}\n".format(
                virtual_machine_name,
                child_compartment_name,
                region
            ))
            print("Please inspect results below.\n\n")
            print(results)
    else:
        print(
            "\n\nINVALID OPTION! - Valid option is:\n\n" +
            "\t--force\t\tDelete the running VM instance\n\n" +
            "Please try again with the correct option.\n\n"
        )
        raise RuntimeWarning("WARNING! Invalid option")
else:
    warning_beep(6)
    print("\nTHIS OPTION CANNOT BE UNDONE.\n")
    print("Enter YES to delete virtual machine instance {} or any other key to abort".format(
        virtual_machine_name
    ))
    if "YES" == input():
        print("\n\nDeleting the VM instance {} from compartment {} within region {}\n".format(
            virtual_machine_name,
            child_compartment_name,
            region
        ))
        print("This will take a few minues to complete, please wait......\n")
        results = terminate_instance(
            compute_composite_client,
            vm_instance.id
        )
        if results is None:
            raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
        else:
            print("Deletion of VM instance {} within compartment {} in region {} completed.\n".format(
                virtual_machine_name,
                child_compartment_name,
                region
            ))
            print("Please inspect the results below.\n\n")
            print(results)