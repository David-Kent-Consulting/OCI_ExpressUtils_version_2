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
from time import sleep

from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import GetLocalPeeringGateway
from lib.gateways import update_local_peering_gateway_router
from lib.routetables import GetRouteTable
from lib.vcns import GetVirtualCloudNetworks

from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core import VirtualNetworkClientCompositeOperations

from oci.core.models import UpdateLocalPeeringGatewayDetails

if len(sys.argv) !=7:
    print(
        "\n\nOci-UpdateLocalPeeringGateway.py : Correct Usage\n\n" +
        "Oci-UpdateLocalPeeringGateway.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[local peering gateway] [route_table] [region]\n\n" +
        "Use case example assigns the specified route table to the local peering gateway\n" +
        "\tOci-UpdateLocalPeeringGateway.py admin_comp auto_comp auto_vcn auto_to_dbs_lpg DmztoIntranetLpg 'us-ashburn-1'\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise ReferenceError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
local_peering_gateway_name  = sys.argv[4]
route_table_name            = sys.argv[5]
region                      = sys.argv[6]

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
network_composite_client = VirtualNetworkClientCompositeOperations(network_client)

print("\n\nFetching and verifying tenant resource date, please wait......")
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

# get LPG data
local_peering_gateways = GetLocalPeeringGateway(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    local_peering_gateway_name
)
local_peering_gateways.populate_local_peering_gateways()
local_peering_gateway = local_peering_gateways.return_local_peering_gateway()

# get route table data
route_tables = GetRouteTable(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    route_table_name
)
route_tables.populate_route_tables()
route_table = route_tables.return_route_table()
error_trap_resource_not_found(
    route_table,
    "Route table " + route_table_name + " not found in virtual cloud network " + virtual_cloud_network_name 
)

print("Applying the replacement route table {} to local peering gateway {}\n".format(
    route_table_name,
    local_peering_gateway_name
))
# Apply the replacement or new route table to the LPG
update_local_peering_gateway_response = update_local_peering_gateway_router(
    network_composite_client,
    UpdateLocalPeeringGatewayDetails,
    local_peering_gateway.id,
    route_table.id
)

if update_local_peering_gateway_response is not None:
    print("Update successful, please review the results below\n")
    sleep(5)
    print(update_local_peering_gateway_response)
else:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR"
)
