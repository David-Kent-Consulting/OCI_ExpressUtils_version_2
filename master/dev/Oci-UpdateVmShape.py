#!/usr/bin/python3

# Copyright 2019 – 2022 David Kent Consulting, Inc.
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
from lib.general import is_int
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.compute import get_vm_instance_response
from lib.compute import GetShapes

# required OCI modules
from oci.config import from_file
from oci import wait_until
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import UpdateInstanceDetails
from oci.core.models import UpdateInstanceShapeConfigDetails

def update_vm_flex_shape(
    instance_id,
    my_flex_shape,
    my_ocpus,
    my_memory_in_gbs):

    # instiate the shape config to the OCI class
    shape_details = UpdateInstanceShapeConfigDetails(
        ocpus = my_ocpus,
        memory_in_gbs = my_memory_in_gbs
    )
    
    # now instiate the instance details class
    instance_details = UpdateInstanceDetails(
        shape = my_flex_shape,
        shape_config = shape_details
    )
    
    # finally, apply the shape change and return the results
    results = compute_client.update_instance(
        instance_id = instance_id,
        update_instance_details = instance_details
    ).data
    return results

# end function update_vm_flex_shape()

    

copywrite()
sleep(2)
if len(sys.argv) < 7 or len(sys.argv) > 11:
    print(
        "\n\nOci-UpdateVmShape.py : Usage\n\n" +
        "Oci-UpdateVmShape.py [parent compartment] [child compartment] [vm name] [shape] [region] [--force/--prompt] [optional arguments]\n\n" +
        "Use case example 1 changes the VM instance shape to VM.Standard2.2 for the specified virtual machine with no user prompt:\n" +
        "\tOci-UpdateVmShape.py admin_comp tst_comp DKCJUBSUBT01 'VM.Standard2.2' 'us-ashburn-1' --force\n" +
        "Use case example 2 changes the VM instance shape's OCPUS to 2 and the memory to 32 Gbyte- only valid for FLEX shapes:\n" +
        "\tOci-UpdateVmShape.py admin_comp web_comp DKCTCATP01 'VM.Standard.E3.Flex' us-ashburn-1' --prompt --ocpus 2 --memory 32\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
shape                           = sys.argv[4]
region                          = sys.argv[5]
if sys.argv[6].upper() == "--FORCE":
    prompt_action = False
else:
    prompt_action = True

options_error = "\n\nINVALID OPTION!\n\nYou must supply the OCPUS first and then the MEMORY as in:\n\tOci-UpdateVmShape.py admin_comp web_comp DKCTCATP01 'VM.Standard.E3.Flex' us-ashburn-1' --prompt --ocpus 2 --memory 32\n\n"
# print(options_error)

if len(sys.argv) == 7:  # required for logic to work when selecting a FLEX shape and failing to provide the correct arguments
    ocpus           = None
    memory_in_gbs   = None

if len(sys.argv) == 11:
    # we will expect that both the OCPUS and Memory will be passed when changing to a FLEX shape.
    if sys.argv[7].upper() == "--OCPUS":
        # shape_option          = "OCPUS"
        if is_int(sys.argv[8]):
            ocpus = int(sys.argv[8])
        else:
            ocpus = None
    else:
        print(options_error)
        raise RuntimeWarning("WARNING! Invalid option")
    if sys.argv[9].upper() == "--MEMORY":
        if is_int(sys.argv[10]):
            memory_in_gbs   = int(sys.argv[10])
        else:
            memory_in_gbs   = None
    else:
        print(options_error)
        raise RuntimeWarning("WARNING! Invalid option")


# set the valid shape sets and other vars

# remove old logic wojteczko 16sep2024
# flex_shapes                 = ["VM.Standard.E3.Flex", "VM.Standard.E4.Flex"]
# standard_shapes             = ["VM.Standard2.1", "VM.Standard2.2", "VM.Standard2.4", "VM.Standard2.8", "VM.Standard2.16", "VM.Standard2.24"]
# end remove

allowed_core_counts         = [1,2,4,8,16,24] # These are the allowed core counts for FLEX shapes
desired_state               = "RUNNING" # This is the desired state of the VM instance to check for after applying the shape change
max_interval_in_seconds     = 30 # time to wait between checking the VM instance state
max_wait_seconds_for_change = 1200 # wait no more than 20 minutes for the shape change to apply

'''
old logic remove wojteczko 16sep2024
if shape not in standard_shapes:
    if shape not in flex_shapes:
        raise RuntimeError("EXCEPTION! Invalid VM instance shape")
    else:
        shape_option = "FLEX"
else:
    shape_option = "STANDARD
'''

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
network_client = VirtualNetworkClient(config) # builds the network client, required to manage network resources

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

# valide the shape selection
my_shapes = GetShapes(compute_client, child_compartment.id)
my_shapes.populate_shapes()
my_shape = my_shapes.return_shape(shape)
if my_shape is None:
    raise RuntimeError("\nWARNING! Shape " + shape + " was not found. Please try again.\n\n")

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


# The instance must be in a running state prior to applying the shape change.
# failure to do so will result in placing the VM in a deadly embrace state
# of updating without ever applying an update, with the only recourse being
# to terminate the instance.
if vm_instance.lifecycle_state != "RUNNING":
    print(
    "\n\nThe VM instance {} must be in a running state in order to safely apply a shape change.\n\n".format(
        virtual_machine_name
    ))
    raise RuntimeError("EXCEPTION! VM Instance not in a running state.")

if prompt_action:

    warning_beep(6)
    print(
        "\nProceeding will result in a disruption of service to the VM instance's\n" +
        "application if in a running state. Please be certain that you have met all\n" +
        "necessary conditions prior to proceeding.\n\n" +
        "Enter YES to update the VM instance " + virtual_machine_name + " shape, any other key to abort"
        )
    if "YES" != input():
        print("Shape change request aborted by user.\n\n")
        raise RuntimeWarning("SHAPE CHANGE REQUEST ABORTED BY USER!")


# update the shape
results = update_vm_flex_shape(
        vm_instance.id,
        shape,
        ocpus,
        memory_in_gbs
    )

if results is None:
    raise RuntimeError("\nRUNTIME ERROR - Check OCI Console for details.\n\n")

print("VM instance " + virtual_machine_name + "shape change request has been submitted. The shape change will take a few minutes to apply.\n\n")
