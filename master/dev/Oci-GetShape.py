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
from lib.compute import GetShapes

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient

copywrite()
sleep(2)
if len(sys.argv) != 5:
    print(
        "\n\nOci-GetShapes.py : Usage\n\n" +
        "Oci-GetShapes.py [parent compartment] [child compartment] [shape] [optional argument]\n\n" +
        "Use case example 1 gets information about all machine shapes within the specified compartment and region:\n" +
        "\tOci-GetShapes.py admin_comp tst_comp list_all_vm_shapes 'us-ashburn-1'\n" +
        "Use case example 2 gets information about the specified VM shape within the specified compartment and region:\n" +
        "\tOci-GetShapes.py admin_comp web_comp 'VM.Standard2.1' 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
shape_name                      = sys.argv[3]
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

# run through the logic
shapes = GetShapes(
    compute_client,
    child_compartment.id
)
shapes.populate_shapes()
# print(shapes.return_all_shapes())


if sys.argv[3].upper() == "LIST_ALL_VM_SHAPES":
    header = [
        "COMPARTMENT",
        "SHAPE",
        "OCPUS",
        "MEMORY",
        "BANDWIDTH IN Gbps",
        "MAX VNICS",
        "CPU DESCRIPTION",
        "REGION"
    ]
    data_rows = []
    for shape in shapes.return_all_shapes():
        data_row = [
            child_compartment_name,
            shape.shape,
            shape.ocpus,
            shape.memory_in_gbs,
            shape.networking_bandwidth_in_gbps,
            str(int(shape.max_vnic_attachments)),
            shape.processor_description,
            region
        ]
        data_rows.append(data_row)

    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    shape = shapes.return_shape(shape_name)
    error_trap_resource_not_found(
        shape,
        "Machine shape " + shape_name + " not found within compartment " + child_compartment_name + " in region " + region
    )
    print(shape)

