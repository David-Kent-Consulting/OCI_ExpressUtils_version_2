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
from tabulate import tabulate
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import warning_beep
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import GetDynamicRouterGateway
from lib.gateways import GetDrgPeeringConnection
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

if len(sys.argv) < 7 or len(sys.argv) > 8:
    print(
        "\n\nOci-GetRpc.py : Usage\n\n" +
        "Oci-GetRpc.py [parent compartment] [child compartment] [ virtual cloud network] " +
        "[dynamic router gateway] [rpc] [region] [optional arguments]\n\n" +
        "Use case example 1 displays all remote peering connections for the specified dynamic router gateway:\n" +
        "\tOci-GetRpc.py admin_comp dbs_comp dbs_vcn dbs_drg list_all_rpcs 'us-ashburn-1'\n" +
        "Use case example 2 displays the remote peering connection for the specified dynamic router gateway\n" +
        "\tOci-GetRpc.py admin_comp vpn_comp vpn0_vcn vpn0_drg vpn0_drg_primaryregion_rpc 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise ResourceWarning("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
dynamic_router_gateway_name     = sys.argv[4]
rpc_name                        = sys.argv[5]
region                          = sys.argv[6]
if len(sys.argv) == 8:
    option = sys.argv[7].upper()
else:
    option = None # required for logic

if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching and validating tenancy resource data......\n")


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

# Get the dynamic router resources, does not use the vcn_id
dynamic_router_gateways = GetDynamicRouterGateway(
    network_client,
    child_compartment.id,
    dynamic_router_gateway_name
)
dynamic_router_gateways.populate_dynamic_router_gateways()
dynamic_router_gateway = dynamic_router_gateways.return_dynamic_router_gateway()

# Get the remote peering connection resources, does not use the vcn_id
remote_peering_connections = GetDrgPeeringConnection(
    network_client,
    child_compartment.id
)
remote_peering_connections.populate_rpc_connections()

# run through the logic and return results based on inputs


if rpc_name.upper() == "LIST_ALL_RPCS" and len(sys.argv) == 7:
    if remote_peering_connections.return_all_rpc_connections() is None:
        print("\n\nNo RPC connections found within dynamic router gateway {} in region {}\n".format(
            dynamic_router_gateway_name,
            region
        ))
        raise(RuntimeWarning("NO RPC RESOURCES FOUND!"))

    header = [
        "COMPARTMENT",
        "VCN",
        "DRG",
        "RPC",
        "PEERING STATUS",
        "LIFECYCLE STATUS",
        "REGION"
    ]
    data_rows = []
    for rpc in remote_peering_connections.return_all_rpc_connections():
        data_row = [
            child_compartment_name,
            virtual_cloud_network.display_name,
            dynamic_router_gateway.display_name,
            rpc.display_name,
            rpc.peering_status,
            rpc.lifecycle_state,
            region
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:

    remote_peering_connection = remote_peering_connections.return_rcp_connection(rpc_name)
    error_trap_resource_not_found(
        remote_peering_connection,
        "Remote peering connection " + rpc_name + " not found within dynamic router gateway " + dynamic_router_gateway_name + " in region " + region
    )

    if len(sys.argv) == 7:
        
        header = [
            "COMPARTMENT",
            "VCN",
            "DRG",
            "RPC",
            "PEERING STATUS",
            "LIFECYCLE STATUS",
            "REGION"
        ]
        data_rows = [[
            child_compartment_name,
            virtual_cloud_network.display_name,
            dynamic_router_gateway.display_name,
            remote_peering_connection.display_name,
            remote_peering_connection.peering_status,
            remote_peering_connection.lifecycle_state,
            region
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\nRPC ID :\t" + remote_peering_connection.id + "\n\n")
    elif option == "--OCID":
        print(remote_peering_connection.id)
    elif option == "--PEERING-STATUS":
        print(remote_peering_connection.peering_status)
    elif option == "--LIFECYCLE-STATE":
        print(remote_peering_connection.lifecycle_state)
    elif option == "--JSON":
        print(remote_peering_connection)
    else:
        print(
            "\n\nINVALID OPTION! Valid options are:\n\n" +
            "\t--ocid\t\t\tPrint the OCID of the RPC resource\n" +
            "\t--peering-status\tPrint the peering status of the RPC\n" +
            "\t--lifecycle-state\tPrint the lifecycle state of the RCP\n" +
            "\t--json\t\t\tPrint all resource data in JSON format and surpress other output\n\n" +
            "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )
        raise RuntimeWarning("INVALID OPTION!")

