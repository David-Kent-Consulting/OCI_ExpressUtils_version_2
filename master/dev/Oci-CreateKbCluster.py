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

# required bsystem modules
import os.path
import sys
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.compute import GetImages
from lib.container import create_cluster
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.container import create_cluster
from lib.container import GetCluster
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.container_engine.models import AddOnOptions
from oci.container_engine.models import ClusterCreateOptions
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations
from oci.container_engine.models import CreateClusterDetails
from oci.container_engine.models import KubernetesNetworkConfig

# hard copy copywrite statement due to conflict with a 3rd party module
# print(
#     "\nCopyright 2019 – 2021 David Kent Cloud Solutions, Inc.,\n" +
#     "David Kent Consulting, Inc., and its subsidiaries. - All rights reserved.\n" +
#     "Use of this software is subject to the terms and conditions found in the\n" +
#     "file LICENSE.TXT. This file is located in the codebase distribution within the\n" +
#     "directory /usr/local/bin/KENT/bin\n"
# )
copywrite()
sleep(2)
if len(sys.argv) != 8: # ARGS PLUS COMMAND
    print(
        "\n\nOci-CreateKbCluster.py : Usage\n" +
        "Oci-CreateKbCluster.py [parent_compartment] [child_compartment] [virtual cloud network] [subnetwork]\n" +
        "[cluster name] [Kubernetes Version] [region]\n\n"
    )
    raise RuntimeError("Usage Error")


# Instiate all vars and classes
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_cloud_network_name          = sys.argv[3]
subnet_name                         = sys.argv[4]
cluster_name                        = sys.argv[5]
kubernetes_version                  = sys.argv[6]
region                              = sys.argv[7]


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
network_client = VirtualNetworkClient(config)
compute_client = ComputeClient(config)
container_client = ContainerEngineClient(config)
container_composite_client = ContainerEngineClientCompositeOperations(container_client)

print("\n\nGetting tenancy resource data from OCI......\n")
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

# get virtual cloud network data
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name
)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
error_trap_resource_not_found(
    virtual_cloud_network,
    "Virtual cloud network " + virtual_cloud_network_name + " not found in compartment " + child_compartment_name
)

# get subnet data
subnets = GetSubnet(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    subnet_name
)
subnets.populate_subnets()
subnet = subnets.return_subnet()
error_trap_resource_not_found(
    subnet,
    "Subnet " + subnet_name + " not found in virtual cloud network " + virtual_cloud_network_name
)
subnet_list = [subnet.id]

# get cluster data, abort if cluster already present
clusters = GetCluster(
    container_client,
    cluster_name,
    child_compartment.id
)
clusters.populate_cluster()
cluster = clusters.return_cluster()
error_trap_resource_found(
    cluster,
    "Cluster " + cluster_name + " already found in compartment " + child_compartment_name +". Duplicates are not permitted."
)

# Create the cluster and exit upon a provisioning state, we use the default CIDRs for a kubernetes cluster.
print("Create of cluster {} in compartment {} within region {} has been started.\n".format(
    cluster_name,
    child_compartment_name,
    region
))
print("It could take some time to complete the cluster build request.\n")
sleep(10)
results = create_cluster(
    container_composite_client,
    AddOnOptions,
    CreateClusterDetails,
    ClusterCreateOptions,
    KubernetesNetworkConfig,
    cluster_name,
    child_compartment.id,
    virtual_cloud_network.id,
    kubernetes_version,
    subnet_list,
    "10.244.0.0/16",
    "10.96.0.0/16"
)

if results is None:
    raise RuntimeError("EXCEPTION! UNABLE TO CREATE CLUSTER DUE TO AN UNKNOWN ERROR.")
else:
    print("\n\nCluster creation of {} is complete. Please inspect the results below.\n".format(cluster_name))
    sleep(10)
    print(results)

