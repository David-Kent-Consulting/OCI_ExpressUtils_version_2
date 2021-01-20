#!/Users/henrywojteczko/bin/python
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
from oci.core import VirtualNetworkClient
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations

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

# classes and functions

class GetParentCompartments:
    '''
    method GetParentCompartments:
    
    This method pulls all parent compartment data using the OCI API and stores to as a dict object
    all compartments that are active. Call like:
         "my_compartments = GetParentCompartment("compartment_name", config, identity_client)

    arguments:

        compartment_name:
            The name of the compartment that is the parent that is the child of the root
            compartment
        config:
            dict object created on the calling program as in "config = oci.config.from_file()"
        identity_client:
            a class object created in the calling program as in
            "identity_client = oci.identity.IdentityClient(config)"

    The config object is created using oci.config.from_file. Your class object must be populated
    only one time to be of use. You may not run a populate a second time. It is notable that the
    entire codebase is dependent on having the parent compartment object from the root
    compartment (tenancy). If a different parent is required, create a new object from this class
    and populate.

    To return the parent compartment name and tenancy, simply print the object. To return the
    parent object, simply call the method after populated as in:
        my_compartments.return_parent_compartment()


    method GetChildCompartments:
    Similar to GetParentCompartments, gets the children from the supplied parent compartment object

    Arguments:

        parent_compartment_id:
            The parent compartment OCID
        config:
           dict object created on the calling program as in "config = oci.config.from_file()"
        identity_client:
            a class object created in the calling program as in
            "identity_client = oci.identity.IdentityClient(config)"

    Method populate_compartments(self)
        This method will read all parent compartments from the root compartment and will append
        self.parent_compartments with all compartments that have an 'ACTIVE' lifecycle state

    Method return_parent_compartment(self)
        This method parses through parent_compartments and returns the parent compartment object
        with the name that matches self.parent_compartment_name if found.
'''
    def __init__(self,parent_compartment_name, config, identity_client):
        self.parent_compartment_name = parent_compartment_name
        self.parent_compartments = []
        self.config = config
        self.identity_client = identity_client
        
    def populate_compartments(self):
        if len(self.parent_compartments) != 0:
            return None
        
        results = self.identity_client.list_compartments(self.config["tenancy"])
        for item in results.data:
            if item.lifecycle_state == 'ACTIVE' or item.lifecycle_state == 'DELETING':
                self.parent_compartments.append(item)
                
    def return_parent_compartment(self):
        for item in self.parent_compartments:
            if item.name == self.parent_compartment_name:
                return item
    
    def __str__(self):
        return "The parent compartment name is " + self.parent_compartment_name + " in tenancy " \
                + self.config["tenancy"]

# end class GetParentCompartments

class GetChildCompartments:
    '''
    This class operates similar to GetParentCompartments, except that it operates from the parent
    compartment object ID provided to it rather than the root compartment ID. It also has methods
    that returns all child compartments, or a select child compartment, if present in child_compartments.
    '''
    def __init__(self, parent_compartment_id, child_compartment_name, identity_client):
        self.parent_compartment_id = parent_compartment_id
        self.child_compartment_name = child_compartment_name
        self.identity_client = identity_client
        self.child_compartments = []
    
    def populate_compartments(self):

        if len(self.child_compartments) != 0:
            return None
        results = self.identity_client.list_compartments(self.parent_compartment_id)
        for item in results.data:
            if item.lifecycle_state == 'ACTIVE' or item.lifecycle_state == 'DELETING':
                self.child_compartments.append(item)
    
    def return_all_child_compartments(self):
        if len(self.child_compartments) == 0:
            return None
        else:
            return self.child_compartments

    def return_child_compartment(self):
        if len(self.child_compartments) == 0:
            return None
        else:
            for item in self.child_compartments:
                if item.name == self.child_compartment_name:
                    return item
                
    def __str__(self):
        return "The child compartment name is " + self.child_compartment_name
                
# end GetChildCompartments

class GetImages:
    
    def __init__(
        self,
        compute_client,
        compartment_id):
        
        self.compute_client = compute_client
        self.compartment_id = compartment_id
        self.image_list = []    # here we will store a list of lists containing the
                                # display_name and image_id objects to save on memory
            
    def populate_image_list(self):

        if len(self.image_list) != 0:
            return None
        else:
            results = self.compute_client.list_images(
                compartment_id = self.compartment_id,
                sort_order = "ASC"
                ).data
            if len(results) > 0:
                for image in results:
                    temp_value = [image.display_name, image.id]
                    self.image_list.append(temp_value)
                    
    def return_image(self, image_name):

        if len(self.image_list) == 0:
            return None
        else:
            for image in self.image_list:
                if image[0] == image_name:
                    results = self.compute_client.get_image(
                        image_id = image[1]
                    ).data
                    if results.lifecycle_state == "AVAILABLE":
                        return results
            return None
    
    def search_for_image(self, search_string):

        if len(self.image_list) == 0:
            return None
        else:
            image_list = [] # we'll store the results here if we find anything
            for image in self.image_list:
                # return len(self.image_list[0][0])
                if search_string.upper() in image[0].upper():
                    image_list.append(image)
            if len(image_list) == 0:
                return None
            else:
                return image_list
    
    def __str__(self):
        return "Class setup to perform tasks for images in compartment id " + self.compartment_id

    # end class GetImages

class GetVirtualCloudNetworks:
    
    def __init__(self, network_client, compartment_id, vcn_name):
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_name = vcn_name
        self.virtual_cloud_networks = []

        
    def populate_virtual_cloud_networks(self):
        if len(self.virtual_cloud_networks) == 0:
            results = self.network_client.list_vcns(compartment_id = self.compartment_id)
            for item in results.data:
                if item.lifecycle_state != "TERMINATED":
                    self.virtual_cloud_networks.append(item)
            
    def return_all_virtual_networks(self):
        return self.virtual_cloud_networks
    
    def return_virtual_cloud_network(self):
        for item in self.virtual_cloud_networks:
            if item.display_name == self.vcn_name:
                return item

# end class GetVirtualCloudNetworks

class GetSubnet:
    
    def __init__(self, network_client, compartment_id, vcn_id, subnet_name):
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.subnet_name = subnet_name
        self.subnets = []
    
    def populate_subnets(self):
        if len(self.subnets) != 0:
            return None
        else:
            results = self.network_client.list_subnets(
                compartment_id = self.compartment_id,
                vcn_id = self.vcn_id
            ).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED" or item.lifecycle_state != "TERMINATING":
                    self.subnets.append(item)
    
    def return_all_subnets(self):
        if len(self.subnets) == 0:
            return None
        else:
            return self.subnets
    
    def return_subnet(self):
        if len(self.subnets) == 0:
            return None
        else:
            for item in self.subnets:
                if item.display_name == self.subnet_name:
                    return item
            
    def __str__(self):
        return "Method setup for performing tasks against " + self.subnet_name

# end class GetSubnet

class GetCluster:
    
    def __init__(
        self,
        container_client,
        cluster_name,
        compartment_id):
        
        self.container_client = container_client
        self.cluster_name = cluster_name
        self.compartment_id = compartment_id
        self.clusters = []
        
    def populate_cluster(self):
        if len(self.clusters) != 0:
            return None
        else:
            results = self.container_client.list_clusters(
                compartment_id = self.compartment_id
            ).data
            for cluster in results:
                if cluster.lifecycle_state == "DELETED" or cluster.lifecycle_state == "DELETING":
                    pass
                else:
                    self.clusters.append(cluster)
                    
    def return_all_cluster(self):
        if len(self.clusters) == 0:
            return None
        else:
            return self.clusters
    
    def return_cluster(self):
        if len(self.clusters) == 0:
            return None
        else:
            for cluster in self.clusters:
                if cluster.name == self.cluster_name:
                    return cluster
    
    def __str__(self):
        return "Class setup to perform tasks on " + self.cluster_name

# end class GetCluster

def create_node_pool(
    container_composite_client,
    CreateNodePoolDetails,
    NodeSourceViaImageDetails,
    CreateNodeShapeConfigDetails,
    CreateNodePoolNodeConfigDetails,
    NodePoolPlacementConfigDetails,
    compartment_id,
    cluster_id,
    node_pool_name,
    kubernetes_version,
    node_shape,
    node_image_id,
    boot_volume_size_in_gbs,
    subnet_id,
    nodes_per_subnet,
    availability_domains
    ):
    
    create_node_pool_details = CreateNodePoolDetails(
        compartment_id = compartment_id,
        cluster_id = cluster_id,
        name = node_pool_name,
        kubernetes_version = kubernetes_version,
        node_shape = node_shape,
        node_source_details = NodeSourceViaImageDetails(
            source_type = "IMAGE",
            image_id = node_image_id,
            boot_volume_size_in_gbs = boot_volume_size_in_gbs
        ),
        node_config_details = CreateNodePoolNodeConfigDetails(
            size = nodes_per_subnet,
            placement_configs = [
                NodePoolPlacementConfigDetails(
                    availability_domain = availability_domains[0],
                    subnet_id = subnet_id
                ),
                NodePoolPlacementConfigDetails(
                    availability_domain = availability_domains[1],
                    subnet_id = subnet_id
                ),
                NodePoolPlacementConfigDetails(
                    availability_domain = availability_domains[2],
                    subnet_id = subnet_id
                )
            ]
        )
    )

    
    results = container_composite_client.create_node_pool_and_wait_for_state(
        create_node_pool_details = create_node_pool_details,
        wait_for_states = ["FAILED", "SUCCEEDED", "CANCELED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    return results

# end function create_node_pool()

def error_trap_resource_not_found(
    item,
    description):
    '''
    Function tests the length of the expected resource item, if null, then print the message and exit with a run time error.
    Use in your code to check for cloud resource objects that you expect to find. Do not use with lists.

    Usage: error_trap_resource_not_found(<object to check for> <descriptive message>)
    '''
    if item is None:
        print(
            "\n\nWARNING! - " + description + "\n\n" +
            "Please try again with a correct resource name\n\n"
            )
        raise RuntimeWarning("WARNING! - Resource not found\n")

# end function error_trap_resource_not_found


def get_availability_domains(
    identity_client,
    compartment_id):
    '''
    
    This function retrieves the availability domains for the specified compartment.
    
    '''
    
    results = identity_client.list_availability_domains(
        compartment_id = compartment_id).data
    
    return results

# end function get_availability_domain

def return_availability_domain(
    identity_client,
    compartment_id,
    ad_number):
    '''
    Function returns the availability domain name based on the inout of the
    compartment ID and the availability zone number. A result of None is
    returned if a number outside of 1-3 is entered for ad_number.
    
    Usage:
        my_ad_name = return_availability_domain(
            compartment_id,
            2)
    returns the name of availability domain 2 within compartment_id
    '''
    
    if ad_number > 0 and ad_number <= 3:
        availability_domains = get_availability_domains(
            identity_client,
            compartment_id)
    
        return availability_domains[ad_number - 1].name
    else:
        return None

    # end function return_availability_domain()

if len(sys.argv) != 13: # ARGS PLUS COMMAND
    print(
        "\n\n410_CreateNodePool.py : Usage\n" +
        "410_CreateNodePool.py [parent_compartment] [child_compartment] [virtual cloud network] [subnet]\n" +
        "[cluster name] [nodepool name] [Kubernetes Version] [shape] [image name] [boot vol size in gbs]\n" +
        "[nodes per subnet] [region]\n\n"
    )
    raise RuntimeError("Invalid number of arguments provided to the script. Consult the script header for required arguments")

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

config = from_file() # gets ~./.oci/config and reads to the object
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