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

# required OCI modules
from lib.general import copywrite
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import add_local_peering_gateway
from lib.gateways import create_local_peering_gateway_details
from lib.gateways import create_lpg_peering
from lib.gateways import GetLocalPeeringGateway
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import ConnectLocalPeeringGatewaysDetails

copywrite()
sleep(2)
if len(sys.argv) != 10:
    print(
        "\n\nOci-CreateLpgPeerConnection.py : Correct Usage\n\n" +
        "Oci-CreateLpgPeerConnection.py [source parent compartment] [source child compartment] [source virtual cloud network]\n" +
        "[source LPG router] [target parent compartment] [target child compartment] [target virtual cloud network]\n" +
        "[target LPG Router] [region]\n\n" +
        "Use case example peers two LPGs\n" +
        "\tOci-CreateLpgPeerConnection.py admin_comp auto_comp auto_vcn auto_to_bas_lpg \\\n" +
        "\tadmin_comp bas_comp bas_vcn bas_to_auto_lpg 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect usage\n")
# in order for the source LPG
s_parent_c      = sys.argv[1]
s_child_c       = sys.argv[2]
s_vcn_name      = sys.argv[3]
s_lpg_name      = sys.argv[4]
# in order for the target LPG
t_parent_c      = sys.argv[5]
t_child_c       = sys.argv[6]
t_vcn_name      = sys.argv[7]
t_lpg_name      = sys.argv[8]
# now the region, which must be the same for both source and target
region          = sys.argv[9]

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

# Now we are going to get all the source LPG data
source_parent_compartments = GetParentCompartments(
    s_parent_c,
    config,
    identity_client)
source_parent_compartments.populate_compartments()
source_parent_compartment = source_parent_compartments.return_parent_compartment()

if source_parent_compartment is None:
    print(
        "\n\nWARNING! - Source parent compartment {} not found\n\n".format(
            s_parent_c
        )
    )
    raise RuntimeWarning("WARNING! Compartment not found\n")

source_child_compartments = GetChildCompartments(
    source_parent_compartment.id,
    s_child_c,
    identity_client)
source_child_compartments.populate_compartments()
source_child_compartment = source_child_compartments.return_child_compartment()

if source_child_compartment is None:
    print(
        "\n\nWARNING! - Source child compartment {} not found\n\n".format(
            s_child_c
        )
    )
    raise RuntimeWarning("WARNING! - Compartment not found\n")
source_virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    source_child_compartment.id,
    s_vcn_name)
source_virtual_cloud_networks.populate_virtual_cloud_networks()
source_virtual_network = source_virtual_cloud_networks.return_virtual_cloud_network()

if source_virtual_network is None:
    print(
        "\n\nWARNING! Source virtual network {} not found\n\n".format(
            s_vcn_name
        )
    )
    raise RuntimeWarning("WARNING! - Virtual cloud network not found\n")
source_local_peering_gateways = GetLocalPeeringGateway(
    network_client,
    source_child_compartment.id,
    source_virtual_network.id,
    s_lpg_name
)
source_local_peering_gateways.populate_local_peering_gateways()
source_local_peering_gateway = source_local_peering_gateways.return_local_peering_gateway()

# Now check to see not only if the source LPG is there, but also if it is in a peering state
if source_local_peering_gateway is None or source_local_peering_gateway.peering_status != "NEW":
    print(
        "\n\nWARNING! - Source LPG {} not present or is not in a correct state\n\n".format(
            s_lpg_name
        )
    )
    raise RuntimeWarning("WARNING! LPG missing or in an incorrect state\n")

# Now get the target LPG data
target_parent_compartments = GetParentCompartments(
    t_parent_c,
    config,
    identity_client
)
target_parent_compartments.populate_compartments()
target_parent_compartment = target_parent_compartments.return_parent_compartment()

if target_parent_compartment is None:
    print(
        "\n\nWARNING! - Parent compartment {} not found\n\n".format(
            t_parent_c
        )
    )
    raise RuntimeWarning("WARNING! Compartment not found\n")
target_child_compartments = GetChildCompartments(
    target_parent_compartment.id,
    t_child_c,
    identity_client
)
target_child_compartments.populate_compartments()
target_child_compartment = target_child_compartments.return_child_compartment()

if target_child_compartment is None:
    print(
        "\n\nWARNING! - Child compartment {} not found\n".format(
            t_child_c
        )
    )
    raise RuntimeWarning("WARNING! - Compartment not found\n")

target_virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    target_child_compartment.id,
    t_vcn_name
)
target_virtual_cloud_networks.populate_virtual_cloud_networks()
target_virtual_cloud_network = target_virtual_cloud_networks.return_virtual_cloud_network()

if target_virtual_cloud_network is None:
    print(
        "\n\nWARNING! - Virtual cloud network {} not found\n\n".format(
            t_vcn_name
        )
    )
    raise RuntimeWarning("WARNING! - Virtual cloud network not found\n")

target_local_peering_gateways = GetLocalPeeringGateway(
    network_client,
    target_child_compartment.id,
    target_virtual_cloud_network.id,
    t_lpg_name
)
target_local_peering_gateways.populate_local_peering_gateways()
target_local_peering_gateway = target_local_peering_gateways.return_local_peering_gateway()

# same as the source LPG
if target_local_peering_gateway is None or source_local_peering_gateway.peering_status != "NEW":
    print(
    "\n\nWARNING! - Target LPG {} not present or is not in a correct state\n\n".format(
        t_lpg_name)
    )
    raise RuntimeWarning("WARNING! LPG missing or in an incorrect state\n")

# If we got this far, we are now ready to create the LPG peering connections.
# We start by creating a method from the OCI API for the remote peer ID, then
# we proceed to create the peer. The LPG peering returns an object value of
# None upon success, or an exception on failure. We choose to not rely on this
# result since it is weak. Instead, we test for the expected results of
# peered LPGs. The function lib.gateways.create_lpg_peering does the first part
# necessary to create the LPG peer connection, we then rely on a call to
# lib.gateways.GetLocalPeeringGateway to verify its state.
create_lpg_peering(
    network_client,
    ConnectLocalPeeringGatewaysDetails,
    source_local_peering_gateway.id,
    target_local_peering_gateway.id
)
print("Waiting for the peering connection to create......\n")
sleep(10) # wait this long prior to checking the state
results = GetLocalPeeringGateway(
    network_client,
    source_child_compartment.id,
    source_virtual_network.id,
    s_lpg_name
)
results.populate_local_peering_gateways()
peering_status_result = results.return_local_peering_gateway()
if peering_status_result.peering_status == "PEERED":
    print(
        "LPG {} sucessfully peered with {}\n".format(
            s_lpg_name,
            t_lpg_name
        )
    )
else:
    print(
        "\n\nWARNING! - LPG {} not properly peered with {}\n".format(
            s_lpg_name,
            t_lpg_name
        ) +
        peering_status_result
        )
    raise RuntimeError("EXCEPTION! Inspect the status of the source LPG for more information\n")

