#!/usr/bin/python3

# Copyright 2019 – 2023 David Kent Consulting, Inc.
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
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetCapacityReservations
from lib.compute import GetInstance

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core.models import UpdateInstanceDetails


copywrite()
sleep(2)

if len(sys.argv) != 7:
    print(
            "\n\nOci-UpdateVmCapacityReservation.py | Usage\n\n" +
            "Oci-UpdateVmCapacityReservation.py [parent compartment] [child compartment] [VM name] [reservation name] [region] [enable/disable]\n" +
            "Use case example 1 enables a capacity reservation for the specified VM:\n" +
            "\tOci-UpdateVmCapacityReservation.py admin_comp bas_comp kentanst01 ad3_reservations 'us-ashburn-1' enable\n" +
            "Use case example 2 disables a capacity reservation for the specified VM and does not prompt for user confirmation:\n" +
            "\tOci-UpdateVmCapacityReservation.py admin_comp bas_comp kentanst01 ad3_reservations 'us-ashburn-1' disable --force\n\n" +
            "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
reservation_name                = sys.argv[4]
region                          = sys.argv[5]
if sys.argv[6].upper() == "ENABLE":
    reservation_state = True
elif sys.argv[6].upper() == "DISABLE":
    reservation_state = False
else:
    raise RuntimeError("\nEXCEPTION! - Reservation state must be ENABLE or DISABLE\n\n")


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

# get availability domains
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
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
    "Virtual Machine " + virtual_machine_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# print(vm_instance)

reservations = GetCapacityReservations(
    compute_client,
    child_compartment.id
)

reservations.populate_capacity_list()

my_reservations = reservations.return_all_capacity_reservations()
my_reservation = reservations.return_capacity_reservation_name(reservation_name)

error_trap_resource_not_found(
    my_reservation,
    "Reservation " + reservation_name + " not found in compartment " + child_compartment_name + "within region " + region
)

# print(my_reservation)

'''
There is a defect as of 14-feb-2023 in the rest API service. If an instance is assigned/removed to/from a
capacity reservation resource, used_instance_count is not incremented/decremented. We work around this
defect by requiring the instance to be in a RUNNING state prior to either adding or removiing it
from the resource.

We add a sleep(120) to allow the resource manager sufficient time to apply the update prior to returning
a result. Undefined program behavior could result in the absence of this delay if the command is
repeated in less time than 120 seconds.
'''

if vm_instance.capacity_reservation_id is not None and reservation_state:
    print("\nVirtual machine {} already assigned to capacity reservartion resource {}\n\n".format(
        virtual_machine_name,
        vm_instance.capacity_reservation_id
    ))
    exit(0)

if vm_instance.availability_domain != my_reservation.availability_domain:
    print("\n\nVM instance {} not in same availability domain as reservation {}\n\n".format(
        virtual_machine_name,
        reservation_name
    ))
    raise RuntimeError("\nEXCEPTION! - Invalid availability domain\n\n")

if my_reservation.reserved_instance_count == my_reservation.used_instance_count and reservation_state:
    print("\n\nInsufficient reservations within {}\n".format(reservation_name))
    raise RuntimeError("EXCEPTION! - Invalid reservation choice\n\n")

if vm_instance.lifecycle_state != "RUNNING":
    print("\nVirtual machine {} not in  RUNNING state. Please start the virtual machine and try again.\n\n".format(virtual_machine_name))
    raise RuntimeError("\nEXCEPTION! - Instance in invalid state.\n\n")

if reservation_state:
    
    update_instance_response = compute_client.update_instance (
        instance_id = vm_instance.id,
        update_instance_details = UpdateInstanceDetails (
            capacity_reservation_id = my_reservation.id
        )
    )
    print("\nApplying capacity reservation request, please wait......\n")
    sleep(120)
    if update_instance_response.data.capacity_reservation_id != my_reservation.id:
        raise RuntimeWarning("\n\nWARNING! See REST API error, resolve issue, and retyr.\n\n")
    else:
        print("Virtual machine {} has been assigned to capacity reservation resource {}\n".format(
            virtual_machine_name,
            reservation_name
        ))

else:
    

    if vm_instance.capacity_reservation_id is None:
        print("Virtual Machine {} is currently not assigned to a capacity reservation resource.\n".format(virtual_machine_name))
    else:
        update_instance_response = compute_client.update_instance(
            instance_id = vm_instance.id,
            update_instance_details = UpdateInstanceDetails (
                capacity_reservation_id = ""
            )
        )
        print("\nApplying capacity reservation removal request, please wait......\n")
        sleep(120)
        if update_instance_response.data.capacity_reservation_id is not None:
            raise RuntimeWarning("WARNING! See REST API error, resolve issue, and retyr.\n\n")
        else:
            print("Virtual machine {} has been removed from capacity reservation resource {}\n".format(
            virtual_machine_name,
            reservation_name
            ))
