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
# required system modules
import os.path
import sys
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import GetInputOptions
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import create_drg_rpc
from lib.gateways import delete_drg_attachment
from lib.gateways import GetDrgPeeringConnection
from lib.gateways import GetDynamicRouterGateway
from lib.routetables import GetRouteTable
from lib.securitylists import GetNetworkSecurityList
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core import VirtualNetworkClientCompositeOperations

# required OCI decorators
from oci.core.models import CreateRemotePeeringConnectionDetails

copywrite()
sleep(2)
if len(sys.argv) != 6:
    print(
        "\n\nOci-AddDrgRemotePeeringConnection.py : Usage\n\n" +
        "Oci-AddDrgRemotePeeringConnection.py [parent compartment] [child compartment]\n" +
        "[dynamic router gateway] [remote peering connection name] [region]\n\n" +
        "Use case example adds the remote peering connection to the dynamic router gateway within the specified compartment:\n" +
        "\tOci-AddDrgRemotePeeringConnection.py admin_comp vpn_comp vpn_drg vpn_drg_rpc 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
dynamic_router_gateway_name = sys.argv[3]
drg_rpc_name                = sys.argv[4]
region                      = sys.argv[5]

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

print("\n\nFetching and validating tenancy resource data, please wait......\n")
# get parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Unable to find parent compartment " + parent_compartment_name + " within tenancy " + config["tenancy"]
)

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Unable to find child compartment " + child_compartment_name + " in parent compartment " + parent_compartment_name
)

# get the dynamic router data
dynamic_router_gateways = GetDynamicRouterGateway(
    network_client,
    child_compartment.id,
    dynamic_router_gateway_name
)
dynamic_router_gateways.populate_dynamic_router_gateways()
dynamic_router_gateway = dynamic_router_gateways.return_dynamic_router_gateway()
error_trap_resource_not_found(
    dynamic_router_gateway,
    "Unable to find dynamic router gateway " + dynamic_router_gateway_name + " within the compartment " + child_compartment_name
)

# check to see if the RPC exists, if so, raise an alarm
drg_rpcs = GetDrgPeeringConnection(
    network_client,
    child_compartment.id
)
drg_rpcs.populate_rpc_connections()
drg_rpc = drg_rpcs.return_rcp_connection(drg_rpc_name)
error_trap_resource_found(
    drg_rpc,
    "Dynamic router gateway peering connection " + drg_rpc_name + " already present in compartment " + child_compartment_name 
)

# proceed to create the RPC resource
print("Creating remote peering connection {} within dynamic router gateway {} ......".format(
    drg_rpc_name,
    dynamic_router_gateway_name
))

connect_remote_peering_connections_response = create_drg_rpc(
    network_client,
    CreateRemotePeeringConnectionDetails,
    child_compartment.id,
    drg_rpc_name,
    dynamic_router_gateway.id
)

if connect_remote_peering_connections_response is None:
    raise RuntimeError("EXCEPTION! - UNKOWN ERROR")
else:
    print(connect_remote_peering_connections_response)

