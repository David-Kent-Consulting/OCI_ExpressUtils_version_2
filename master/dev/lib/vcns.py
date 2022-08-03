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

from oci import config
import oci

# config = oci.config.from_file()
# network_client = oci.core.VirtualNetworkClient(config)


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
                    if item.lifecycle_state != "TERMINATING":
                        self.virtual_cloud_networks.append(item)
            
    def return_all_virtual_networks(self):
        return self.virtual_cloud_networks
    
    def return_virtual_cloud_network(self):
        for item in self.virtual_cloud_networks:
            if item.display_name == self.vcn_name:
                return item

# end class GetVirtualCloudNetworks

def add_virtual_cloud_network(
                              network_client,
                              compartment_id,
                              vcn_name,
                              dns_label,
                              cidr_block):
    
    # This OCI method is passed to create_vcn
    vcn_details = oci.core.models.CreateVcnDetails(
        compartment_id = compartment_id,
        display_name = vcn_name,
        dns_label = dns_label,
        cidr_block = cidr_block
    )
    results = network_client.create_vcn(
        create_vcn_details = vcn_details
    ).data

    # Your code must handle the exception if the return type is None
    if results is None:
        raise RuntimeError("EXCEPTION! VCN could not be created.")
    else:
        return results

# end add_virtual_cloud_network()

def delete_virtual_cloud_network(network_client, vcn_id):
    results = network_client.delete_vcn(vcn_id)

    if results is None:
        raise RuntimeError("EXCEPTION! VCN could not be found or deleted.")
    else:
        return results
