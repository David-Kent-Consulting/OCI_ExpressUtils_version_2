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

import os.path
import sys
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import add_local_peering_gateway
from lib.gateways import create_local_peering_gateway_details
from lib.gateways import GetLocalPeeringGateway
from lib.routetables import GetRouteTable
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import CreateLocalPeeringGatewayDetails

config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources

if len(sys.argv) != 7:
    print(
        "\n\nOci-AddLocalPeeringGateway.py : Correct Usage\n\n" +
        "Oci-AddLocalPeeringGateway.py [parent compartment] [child compartment] [virtual network] " +
        "[route table] [local peering gateway name] [region]\n\n" +
        "Use case example creates the local peering gateway within the specified virtual cloud network\n\n" +
        "\tOci-AddLocalPeeringGateway.py admin_comp auto_comp auto_vcn auto_rtb auto_to_dbs_lpg 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
route_table_name                = sys.argv[4]
local_peering_gateway_name      = sys.argv[5]
region                          = sys.argv[6]

# instiate dict and method objects
config = from_file() # gets ~./.oci/config and reads to the object
config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources

# Get the parent compartment
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
if parent_compartment is None:
    print(
        "\n\nWARNING! - Parent compartment {} not found in tenancy {}.\n".format(
            parent_compartment_name,
            config["tenancy"] +
        "Please try again with a correct compartment name.\n\n"
        )
    )
    raise RuntimeWarning("WARNING! - Compartment not found\n")

# get the child compartment
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
if child_compartment is None:
    print(
        "\n\nWARNING! - Child compartment {} not found in parent compartment {}\n".format(
            child_compartment_name,
            parent_compartment_name
        ) +
        "Please try again with a correct compartment name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Compartment not found\n")

# Get the VCN resource
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
if virtual_cloud_network is None:
    print(
        "\n\nWARNING! - Virtual cloud network {} not found in child compartment {}.\n".format(
            virtual_cloud_network_name,
            child_compartment_name
        ) +
        "Please try again with a correct virtual cloud network name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Virtual cloud network not found\n")

# Get the router table resource
route_tables = GetRouteTable(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    route_table_name
)
route_tables.populate_route_tables()
route_table = route_tables.return_route_table()

if route_table is None:
    print(
        "\n\nWARNING! - Route table {} not found within virtual cloud network {}\n".format(
            route_table_name,
            virtual_cloud_network_name
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Route table not found\n")

# Get the LPG resources
local_peering_gateways = GetLocalPeeringGateway(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    local_peering_gateway_name
)
local_peering_gateways.populate_local_peering_gateways()
local_peering_gateway = local_peering_gateways.return_local_peering_gateway()

# Run through the logic
if local_peering_gateway is None:
    # Create the method object for the LPG details
    local_gateway_peering_details = create_local_peering_gateway_details(
        CreateLocalPeeringGatewayDetails,
        child_compartment.id,
        local_peering_gateway_name,
        route_table.id,
        virtual_cloud_network.id
    )
    # The API returns a response of type None if successful, otherwise it returns an exception.
    results = add_local_peering_gateway(
        network_client,
        local_gateway_peering_details
    )
    if results is not None:
        print(
            "Local peering gateway {} created within virtual cloud network {}\n\n".format(
                local_peering_gateway_name,
                virtual_cloud_network_name
            )
        )
    else:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR\n")
else:
    print(
        "\n\nWARNING! - Local perring gateway {} already present within virtual cloud network {}\n".format(
            local_peering_gateway_name,
            virtual_cloud_network_name
        ) +
        "This utility does not permit duplicate local peering gateway resources in the same VCN.\n" +
        "Please try again with a unique name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Duplicate local peering gateway\n")