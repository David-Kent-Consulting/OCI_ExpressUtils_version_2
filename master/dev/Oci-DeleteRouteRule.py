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
from lib.general import get_regions
from lib.routetables import delete_route_rule
from lib.routetables import define_route_rule
from lib.routetables import GetRouteTable
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import RouteRule
from oci.core.models import UpdateRouteTableDetails


if len(sys.argv) != 10:
    print(
        "\n\nOci-DeleteRouteRule.py : Correct Usage\n\n" +
        "Oci-DeleteRouteRule.py [route type] [parent compartment] [child compartment] [virtual cloud network] " +
        "[route table] [gateway name] [destination type] [destination address] [region]\n\n" +
        "Use case example deletes an LPG route to the specified route table\n" +
        "\tOciDeleteRouteTable.py --lpg-type admin_comp auto_comp auto_vcn auto_rtb auto_to_web_lpg \\\n" +
        "\tCIDR_BLOCK '10.1.6.0/23' 'us-ashburn-1'\\\n"+
        "\t'This is the route to the production app tier virtual cloud network'\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect usage\n")

router_type                 = sys.argv[1].upper()
parent_compartment_name     = sys.argv[2]
child_compartment_name      = sys.argv[3]
virtual_cloud_network_name  = sys.argv[4]
route_table_name            = sys.argv[5]
network_entity_name         = sys.argv[6]
destination_type            = sys.argv[7].upper()
destination                 = sys.argv[8]
region                      = sys.argv[9]

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
        "\n\nWARNING! - Route table {} not found in virtual cloud network {}\n".format(
            route_table_name,
            virtual_cloud_network_name
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise RuntimeWarning("WARNING! Route table not found\n")

# Now we must select the correct network entity. We import the correct module and create
# a method called network_entities based on the type of response.
if router_type == "--LPG-TYPE":
    from lib.gateways import GetLocalPeeringGateway
    network_entities = GetLocalPeeringGateway(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        network_entity_name
    )
    network_entities.populate_local_peering_gateways()
    network_entity = network_entities.return_local_peering_gateway()
elif router_type == "--NGW-TYPE":
    from lib.gateways import GetNatGateway
    network_entities = GetNatGateway(
        network_client,
        child_compartment.id,
        virtual_cloud_network,
        network_entity_name
    )
    network_entities.populate_nat_gateways()
    network_entity = network_entities.return_nat_gateway()
elif router_type == "--IGW-TYPE":
    from lib.gateways import GetInternetGateway
    network_entities = GetInternetGateway(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        network_entity_name
    )
    network_entities.populate_internet_gateways()
    network_entity = network_entities.return_internet_gateway()
elif router_type == "--DRG-TYPE":
    from lib.gateways import GetDynamicRouterGateway
    network_entities = GetDynamicRouterGateway(
        network_client,
        child_compartment.id,
        network_entity_name
    )
    network_entities.populate_dynamic_router_gateways()
    network_entity = network_entities.return_dynamic_router_gateway()
    print(network_entity)
else:
    print(
        "\n\nInvalid option. Valid options are:\n" +
        "\t--lpg-type\t: local peering gateway\n" +
        "\t--ngw-type\t: nat gateway\n" +
        "\t--igw-type\t: internet gateway\n" +
        "\t--drg-type\t: dynamic routing gateway\n\n" +
        "Please try again with a correct option.\n\n"
    )
    raise RuntimeWarning("WARNING! - Invalid option\n")

if network_entity is None:
    print(
        "\n\nWARNING! Network router entity {} not found in virtual cloud network {}\n".format(
            network_entity_name,
            virtual_cloud_network_name
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise RuntimeWarning("\n\nWARNING! - Network entity not found\n")

# now delete the route to the route table
results = delete_route_rule(
    network_client,
    UpdateRouteTableDetails,
    route_table.id,
    network_entity,
    destination
)

if results is not None:
    print(results)
else:
    print(
        "\n\nWARNING! Route rule {} not found associated with router {}\n".format(
            destination,
            network_entity_name
        ) +
        "Please check your inputs against the current route table and try again\n\n"
    )
    raise RuntimeWarning("WARNING! - Route not found\n")