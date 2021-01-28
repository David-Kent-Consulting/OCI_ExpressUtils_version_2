#!/Users/henrywojteczko/bin/python3
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

# required built-in modules
import os.path
import sys
from time import sleep

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations

# required DKC modules
from lib.general import error_trap_resource_not_found
from lib.general import warning_beep
from lib.compute import GetImages
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.general import get_regions
from lib.container import GetCluster
from lib.container import get_node_pool

if len(sys.argv) < 6 or len(sys.argv) > 7: # ARGS PLUS COMMAND
    print(
        "\n\nGetNodePool.py : Usage\n" +
        "GetNodePool.py [parent_compartment] [child_compartment] [cluster name] [node pool name]\n" +
        "[region] [optional arguments]\n\n"
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
    print(node_pool)
elif option == "--OCID":
    print(node_pool.id)
elif option == "--NAME":
    print(node_pool.name)
elif option == "--VERSION":
    print(node_pool.kubernetes_version)
elif option == "--NODE-CONFIG":
    print(node_pool.node_config_details)
elif option == "--NODE-IMAGE":
    print(node_pool.node_image_name)
elif option == "--SHAPE":
    print(node_pool.node_shape)
elif option == "--VOL-SIZE":
    print(node_pool.node_source_details.boot_volume_size_in_gbs)

else:
    print(
        "\n\nINVALID OPTION! - Valid options are:\n" +
        "\t--ocid\t\tPrints the OCID of the nodepool resource\n" +
        "\t--name\t\tPrints the name of the nodepool resource\n" +
        "\t--version\tPrints the version of kubernetes\n" +
        "\t--node-config\tPrints the node configuration details\n" +
        "\t--shape\t\tPrints the shape deployed to the nodepool\n"
    )
    raise RuntimeWarning("INVALID OPTION")


