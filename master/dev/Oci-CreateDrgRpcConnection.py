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
from tabulate import tabulate

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import create_drg_rpc_connection
from lib.gateways import GetDrgAttachment
from lib.gateways import GetDrgPeeringConnection
from lib.gateways import GetDynamicRouterGateway

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import ConnectRemotePeeringConnectionsDetails

copywrite()
sleep(2)
if len(sys.argv) != 11:
    print(
        "\n\nOci-CreateDrgRpcConnection.py : Usage\n\n" +
        "Oci-CreateRpgConnection.py [parent compartment] [child compartment] [DRG] [RPC] [region]\n" +
        "[peer parent compartment] [peer child compartment] [peer DRG] [peer RPC] [peer region]\n\n" +
        "Use case example peers the two RPCs in from the specified regions to connect using the\n" +
        "specified RPCs:\n" +
        "\tOci-CreateDrgRpcConnection.py admin_comp dbs_comp dbs_drg dbs_drg_rpc 'us-ashburn-1' \\\n" +
        "\t   admin_comp dr_comp dr_drg dr_drg_rpc 'us-phoenix-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
drg_name                                = sys.argv[3]
rpc_name                                = sys.argv[4]
region                                  = sys.argv[5]
peer_parent_compartment_name            = sys.argv[6]
peer_child_compartment_name             = sys.argv[7]
peer_drg_name                           = sys.argv[8]
peer_rpc_name                           = sys.argv[9]
peer_region                             = sys.argv[10]

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

# also check the peer region
correct_region = False
for rg in regions:
    if rg.name == peer_region:
        correct_region = True
if not correct_region:
    print("\n\nWARNING! - Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        peer_region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources
peer_config = config
peer_config["region"] = peer_region
peer_network_client = VirtualNetworkClient(peer_config)

print("\n\nFetching tenancy resources and validating.......\n")
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
    drg_name
)
dynamic_router_gateways.populate_dynamic_router_gateways()
dynamic_router_gateway = dynamic_router_gateways.return_dynamic_router_gateway()
error_trap_resource_not_found(
    dynamic_router_gateway,
    "Unable to find dynamic router gateway " + drg_name + " within compartment " + child_compartment_name 
)

# now do the same for the peer region
for compartment in parent_compartments.parent_compartments:
    if compartment.name == peer_parent_compartment_name:
        peer_parent_compartment = compartment
error_trap_resource_not_found(
    peer_parent_compartment,
    "Peering compartment " + peer_parent_compartment_name + " not found in tenancy " + config["tenancy"] 
)

peer_child_compartments = GetChildCompartments(
    parent_compartment.id,
    peer_child_compartment_name,
    identity_client
)
peer_child_compartments.populate_compartments()
peer_child_compartment = peer_child_compartments.return_child_compartment()
error_trap_resource_not_found(
    peer_child_compartment,
    "Peer child compartment " + peer_child_compartment_name + " not found in parent compartment " + peer_parent_compartment_name
)

peer_dynamic_router_gateways = GetDynamicRouterGateway(
    peer_network_client,
    peer_child_compartment.id,
    peer_drg_name
)
peer_dynamic_router_gateways.populate_dynamic_router_gateways()
peer_dynamic_router_gateway = peer_dynamic_router_gateways.return_dynamic_router_gateway()
error_trap_resource_not_found(
    peer_dynamic_router_gateway,
    "Peer dynamic router gateway " + peer_drg_name + "not found in compartment " + peer_child_compartment_name 
)

# Make sure the peer connections exist in the primary region
rcps = GetDrgPeeringConnection(
    network_client,
    child_compartment.id
)
rcps.populate_rpc_connections()
rpc = rcps.return_rcp_connection(rpc_name)
error_trap_resource_not_found(
    rpc,
    "Remote peering connection " + rpc_name + " not found within DRG " + drg_name + " in region " + region
)

# Do the same for the remote region
peer_rpcs = GetDrgPeeringConnection(
    peer_network_client,
    peer_child_compartment.id
)
peer_rpcs.populate_rpc_connections()
peer_rpc = peer_rpcs.return_rcp_connection(peer_rpc_name)
error_trap_resource_not_found(
    peer_rpc,
    "Peer RPC " + peer_rpc_name + " not found within DRG " + peer_drg_name + " in region " + peer_region
)

# make sure the RPCs are both in a NEW state
if rpc.peering_status != "NEW" and peer_rpc.peering_status != "NEW":
    warning_beep(1)
    print(
        "\n\nWARNING! - RPC connections are not in a NEW state.\n" +
        "This utility cannot create the RPC connection. Please\n" +
        "inspect the information below and take action as appropriate.\n\n" +
        "See https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/remoteVCNpeering.htm\n" +
        "for more information.\n\n"
    )
    header = [
        "Primary RPC",
        "Primary RPC Peering Status",
        "Primary RPC State",
        "Remote RPC",
        "Remote RPC Peering Status",
        "Remote RPC State"
        ]
    data_row = [[
        rpc.display_name,
        rpc.peering_status,
        rpc.lifecycle_state,
        peer_rpc.display_name,
        peer_rpc.peering_status,
        peer_rpc.lifecycle_state
    ]]
    print(tabulate(data_row, headers = header, tablefmt = "simple"))
    raise RuntimeWarning("INVALID RPC PEERING STATE")


# Create the RPC connection between the two RPCs
print("Creating the RPC connection between the peers {} and {} , this will take several minutes to complete.......\n".format(
    rpc_name,
    peer_rpc_name
))

connect_remote_peering_connections_response = create_drg_rpc_connection(
    network_client,
    ConnectRemotePeeringConnectionsDetails,
    rpc.id,
    peer_rpc.id,
    peer_region
)
# Yah, real flaky, no response from the API, code must now check for the connection
# Oracle  SR 3-25193783141 opened 11-feb-2021, API does not return a value when called.
# We found that sleeping for 3 minutes does the trick.
sleep(180)

# validate that the peering connection created. This is a work-around due to defect reported
# in SR 3-25193783141

# validate the RPC peering by checking one of the RPCs in the peer for a valid peering state
peered_rpc = network_client.get_remote_peering_connection(remote_peering_connection_id = rpc.id).data
if peered_rpc.peering_status == "PEERED":
    print("\nPeering successful, please inspect the results below:\n")
    print(peered_rpc)
else:
    raise RuntimeError("EXCEPTION! PEERING IN INVALID STATE.")