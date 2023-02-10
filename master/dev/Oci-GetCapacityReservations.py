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

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient

copywrite()
sleep(2)

if len(sys.argv) != 5:
    print(
        "\n\nOci-GetCapacityReservations.py : Usage\n\n" +
        "Oci-GetCapacityReservations.py [parent compartment] [child compartment] [reservation name] [region]\n" +
        "Use case example 1 gets all capacity reservation within the specified compartment and region:\n" +
        "\tOci-GetCapacityReservations.py admin_comp bas_comp list_all_reservations 'us-ashburn-1'\n" +
        "Use case example 2 gets the capacity reservations for the specified capacity reservation name:\n" +
        "\tOci-GetCapacityReservations.py admin_comp bas_comp AD2_Reservations 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
reservation_name                = sys.argv[3]
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

reservations = GetCapacityReservations(
    compute_client,
    child_compartment.id
)
reservations.populate_capacity_list()
# print(reservations.reservation_list)
my_reservations = reservations.return_all_capacity_reservations()

error_trap_resource_not_found(
    my_reservations,
    "No capacity reservations found in compartment " + child_compartment_name + " within region " + region
)

header = [
    "COMPARTMENT",
    "RESERVATION\nNAME",
    "RESERVED\nINSTANCE\nCOUNT",
    "USED\nINSTANCE\nCOUNT",
    "REGION\n",
    "OCID"
]



if reservation_name.upper() == "LIST_ALL_RESERVATIONS":

    data_rows = []
    for res in my_reservations:

        data_row = [
            child_compartment_name,
            res.display_name,
            res.reserved_instance_count,
            res.used_instance_count,
            region,
            res.id
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))
    exit(0)

else:
    
    my_rerservation = reservations.return_capacity_reservation_name(reservation_name)
    if my_rerservation is not None:

        data_rows = [[
            child_compartment_name,
            my_rerservation.display_name,
            my_rerservation.reserved_instance_count,
            my_rerservation.used_instance_count,
            region,
            my_rerservation.id
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
    
    else:

        print("Capacity Reservation {} not found in compartment {} within region {}\n\n".format(
            reservation_name,
            child_compartment_name,
            region
        ))

