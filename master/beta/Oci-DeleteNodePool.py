#!/usr/bin/python3
# Modify the above entry to point to the client's python3 virtual environment prior to execution

'''
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

# required system modules
import os.path
import sys
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compute import GetImages
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.container import GetCluster
from lib.container import delete_node_pool
from lib.container import get_node_pool

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7: # ARGS PLUS COMMAND
    print(
        "\n\nOci-DeleteNodePool.py : Usage\n" +
        "Oci-DeleteNodePool.py [parent_compartment] [child_compartment] [cluster name] [node pool name]\n" +
        "[region] [optional argument]\n\n" +
        "Use case example deletes the specified node pool from the specified cluster:\n" +
        "\tOci-DeleteNodePool.py acad_comp math_comp MATHKBC01 MATHKBC01_NP01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("Usage Error")

# Instiate all vars and classes
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
cluster_name                        = sys.argv[3]
node_pool_name                      = sys.argv[4]
region                              = sys.argv[5]
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
container_client = ContainerEngineClient(config) # builds method for container client
container_composite_client = ContainerEngineClientCompositeOperations(container_client)

# get parent compartment data
parent_compartments = GetParentCompartments(
    parent_compartment_name,
    config,
    identity_client
)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found in tenancy " + config["tenancy"]
)

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client
)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Child compartment " + child_compartment_name + " not found in parent compartment " + parent_compartment_name
)


# get cluster data
clusters = GetCluster(
    container_client,
    cluster_name,
    child_compartment.id
)
clusters.populate_cluster()
cluster = clusters.return_cluster()
error_trap_resource_not_found(
    cluster,
    "Cluster " + cluster_name + " not found in compartment " + child_compartment_name
)

# get the nodepool data
node_pools = get_node_pool(
    container_client,
    child_compartment.id,
    cluster.id
)

# get the nodepool
node_pool = None
for np in node_pools:
    if np.name == node_pool_name:
        node_pool = np
error_trap_resource_not_found(
    node_pool,
    "Nodepool " + node_pool_name + " not associated with cluster " + cluster_name
)

# run through the logic
if len(sys.argv) == 6:
    warning_beep(6)
    print("Enter YES to proceed with deletion of nodepool {} from cluster {} or any other key to abort\n".format(
        node_pool_name,
        cluster_name
    ))
    if "YES" != input():
        print("Nodepool delete request aborted per user request.\n")
        exit(0)
elif option != "--FORCE":
    print("\n\nINVALID OPTION! The only valid option is --force. Please try again.\n\n")
    raise RuntimeWarning("INVALID OPTION")

# delete the nodepool
results = None
results = delete_node_pool(
    container_composite_client,
    node_pool.id
)

if results is not None:
    print("\n\nDeletion of nodepool {} from cluster {} completed.\n\n".format(
        node_pool_name,
        cluster_name
    ))
else:
    raise RuntimeError("EXCEPTION - UNKNOWN ERROR")

