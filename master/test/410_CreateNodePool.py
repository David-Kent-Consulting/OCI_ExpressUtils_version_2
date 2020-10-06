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
import oci
import os.path
import sys

if len(sys.argv) != 13: # ARGS PLUS COMMAND
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')

compartment_id              = sys.argv[1]
nodepool_name               = sys.argv[2]
cluster_id                  = sys.argv[3]
kubernetes_version          = sys.argv[4]
node_image_name             = sys.argv[5]
node_shape                  = sys.argv[6]
availability_domain_1       = sys.argv[7]
availability_domain_2       = sys.argv[8]
availability_domain_3       = sys.argv[9]
subnet_id                   = sys.argv[10]
quantity_per_subnet         = sys.argv[11]
ssh_key                     = sys.argv[12]

print(compartment_id+"\n")
print(nodepool_name+"\n")
print(cluster_id+"\n")
print(kubernetes_version+"\n")
print(node_image_name+"\n")
print(node_shape+"\n")
print(availability_domain_1+"\n")
print(availability_domain_2+"\n")
print(availability_domain_3+"\n")
print(subnet_id+"\n")
print(str(quantity_per_subnet)+"\n")
print(ssh_public_key_path+"\n")
exit(0)



# Default config file and profile
config = oci.config.from_file()
container_engine_client = oci.container_engine.ContainerEngineClient(config)



try:
    
    #with open(ssh_public_key_path, mode='r') as file:
     #   ssh_key = file.read()

    placement_config_details = []
    node_placement_config = oci.container_engine.models.NodePoolPlacementConfigDetails(
        availability_domain = availability_domain_1,
        subnet_id = subnet_id
    )
    placement_config_details.append(node_placement_config)
    node_placement_config = oci.container_engine.models.NodePoolPlacementConfigDetails(
        availability_domain = availability_domain_2,
        subnet_id = subnet_id
    )  
    placement_config_details.append(node_placement_config)
    node_placement_config = oci.container_engine.models.NodePoolPlacementConfigDetails(
        availability_domain = availability_domain_3,
        subnet_id = subnet_id
    )  
    placement_config_details.append(node_placement_config)
    
    create_nodepool_node_config_details = oci.container_engine.models.CreateNodePoolNodeConfigDetails(
        placement_configs = placement_config_details,
        size = 3
    )

    create_nodepool_details = oci.container_engine.models.CreateNodePoolDetails(
        cluster_id = cluster_id,
        compartment_id = compartment_id,
        kubernetes_version = kubernetes_version,
        name = nodepool_name,
        node_config_details = create_nodepool_node_config_details,
        node_image_name = node_image_name,
        node_shape = node_shape,
        ssh_public_key = ssh_key
    )
    print(create_nodepool_node_config_details)
    create_nodepool_results = container_engine_client.create_node_pool(create_nodepool_details).data

    print('\n')
    print('===========================')
finally:

    print("Please inspect the returned messages to determine success or failure.\n")

