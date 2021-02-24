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

# required built-in modules
import os.path
import sys
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import get_availability_domains
from lib.general import return_availability_domain
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.compute import GetImages
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.container import create_node_pool
from lib.container import GetCluster
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations

# required OCI decorators
from oci.container_engine.models import AddOnOptions
from oci.container_engine.models import CreateClusterDetails
from oci.container_engine.models import CreateNodePoolDetails
from oci.container_engine.models import CreateNodeShapeConfigDetails
from oci.container_engine.models import CreateNodePoolNodeConfigDetails
from oci.container_engine.models import ClusterCreateOptions
from oci.container_engine.models import KubernetesNetworkConfig
from oci.container_engine.models import NodePoolNodeConfigDetails
from oci.container_engine.models import NodePoolPlacementConfigDetails
from oci.container_engine.models import NodeSourceViaImageDetails

copywrite()
sleep(2)
if len(sys.argv) != 13: # ARGS PLUS COMMAND
    print(
        "\n\nCreateNodePool.py : Usage\n" +
        "CreateNodePool.py [parent_compartment] [child_compartment] [virtual cloud network] [subnetwork]\n" +
        "[cluster name] [nodepool name] [Kubernetes Version] [shape] [image name] [boot vol size in gbs]\n" +
        "[nodes per subnet] [region]\n\n"
    )
    raise RuntimeError("Usage Error")

# Instiate all vars and classes
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_cloud_network_name          = sys.argv[3]
subnet_name                         = sys.argv[4]
cluster_name                        = sys.argv[5]
node_pool_name                      = sys.argv[6]
kubernetes_version                  = sys.argv[7]
shape                               = sys.argv[8]
image_name                          = sys.argv[9]
boot_vol_size_in_gbs                = int(sys.argv[10])
nodes_per_subnet                    = int(sys.argv[11])
region                              = sys.argv[12]

if nodes_per_subnet % 3 != 0:
    raise RuntimeError("Nodes per subnet must be divisable by 3")

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

# get the availability domains, must be a list that will later be passed to create_node_pool()
# All 3 AD names are required since we spread the nodes in each nodepool across the 3 domains
# for resiliancy purposes.
availability_domains = []
for ad_number in [1,2,3]:
    availability_domain = return_availability_domain(
        identity_client,
        child_compartment.id,
        ad_number)
    availability_domains.append(availability_domain)

images = GetImages(
    compute_client,
    child_compartment.id
)
images.populate_image_list()
image = images.return_image(image_name)
error_trap_resource_not_found(
    image,
    "Image " + image_name + " not found in tenancy."
)

# create the nodepool
print("Creating the nodepool......\n")
results = create_node_pool(
    container_composite_client,
    CreateNodePoolDetails,
    NodeSourceViaImageDetails,
    CreateNodeShapeConfigDetails,
    CreateNodePoolNodeConfigDetails,
    NodePoolPlacementConfigDetails,
    child_compartment.id,
    cluster.id,
    node_pool_name,
    kubernetes_version,
    shape,
    image.id,
    boot_vol_size_in_gbs,
    subnet.id,
    nodes_per_subnet,
    availability_domains
)

# print the results and exit
print("\nNodepool creation is completed.\n")
print(results)