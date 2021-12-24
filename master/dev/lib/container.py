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

import os
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
                if cluster.lifecycle_state != "DELETED":
                    if cluster.lifecycle_state != "DELETING":
                        self.clusters.append(cluster)
                    
    def return_all_clusters(self):
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

def get_node_pool(
    container_client,
    compartment_id,
    cluster_id):
    '''
    Function returns the nodepool resource associated with the specified
    cluster_id within the specified compartment_id. Normally we would build
    this in a class. Since the API will bind its response to cluster_id,
    we choose the simplicity of this fuction instead.
    '''
    results = container_client.list_node_pools(
        compartment_id = compartment_id,
        cluster_id = cluster_id
    ).data
    
    return results

# end function get_node_pool()

def create_cluster(
    container_composite_client,
    AdOnOptions,
    CreateClusterDetails,
    ClusterCreateOptions,
    KubernetesNetworkConfig,
    name,
    compartment_id,
    vcn_id,
    kubernetes_version,
    service_lb_subnet_ids,
    pods_cidr,
    services_cidr,
    ):
    
    create_cluster_details = CreateClusterDetails(
        name = name,
        compartment_id = compartment_id,
        vcn_id = vcn_id,
        kubernetes_version = kubernetes_version,
        options = ClusterCreateOptions(
            service_lb_subnet_ids = service_lb_subnet_ids,
            kubernetes_network_config = KubernetesNetworkConfig(
                pods_cidr = pods_cidr,
                services_cidr = services_cidr
            ),
            add_ons = AddOnOptions(
                is_kubernetes_dashboard_enabled = True,
                is_tiller_enabled = False
            )
        )
    )
    
    results = container_composite_client.create_cluster_and_wait_for_state(
        create_cluster_details = create_cluster_details,
        wait_for_states = ["SUCCEEDED", "CANCELED", "FAILED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    return results

# end function create_cluster

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
        wait_for_states = ["IN_PROGRESS", "FAILED", "SUCCEEDED", "CANCELED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    return results

# end function create_node_pool()

def delete_cluster(
    container_client,
    cluster_id
    ):
    '''
    This function deletes the kubernetes cluster cluster_id from the tenancy.
    Your code must handle any prompted for safe removal of the cluster. The
    function returns None if the delete action is unsuccessful.
    '''

    results = container_client.delete_cluster(
        cluster_id = cluster_id
    )

    # results = "test_return_result"

    if results is not None:
        return results
    else:
        return None

# end function delete_cluster()

def delete_node_pool(
    container_composite_client,
    node_pool_id
    ):

    results = container_composite_client.delete_node_pool_and_wait_for_state(
        node_pool_id = node_pool_id,
        wait_for_states = ["SUCCEEDED"]
    )
    if results is not None:
        return results
    else:
        return None

# end function delete_node_pool()

def upgrade_kubernetes_backplane(
    container_client,
    UpdateClusterDetails,
    cluster_id,
    kubernetes_version
    ):
    
    update_cluster_details = UpdateClusterDetails(
        kubernetes_version = kubernetes_version
    )
    
    update_cluster_response = container_client.update_cluster(
        cluster_id = cluster_id,
        update_cluster_details = update_cluster_details
    )
    
    return update_cluster_response.data

# end function kubernetes_version