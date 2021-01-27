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
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.general import get_regions
from lib.gateways import add_local_peering_gateway
from lib.gateways import create_local_peering_gateway_details
from lib.gateways import create_lpg_peering
from lib.gateways import GetLocalPeeringGateway
from lib.vcns import GetVirtualCloudNetworks

from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetLocalPeeringGateway.py : Correct Usage\n\n" +
        "Oci-GetLocalPeeringGateway.py [parent compartment] [child compartment] [virtual network] " +
        "[local peering gateway] [region] [optional argument]\n\n" +
        "Use case example 1 lists all local peering gateways within the virtual cloud network\n" +
        "\tOci-GetLocalPeeringGateway.py admin_comp auto_comp auto_vcn list_all_lpgs 'us-ashburn-1'\n\n"
        "Use case example 2 lists the local peering gateway within the specified virtual cloud network\n" +
        "\tOci-GetLocalPeeringGateway.py admin_comp auto_comp auto_vcn auto_to_bas_lpg 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
lpg_name                    = sys.argv[4]
region                      = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = [] # required for logic to work

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

# get parent compartment data
parent_compartments = GetParentCompartments(
    parent_compartment_name,
    config,
    identity_client
)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()

if parent_compartment is None:
    print(
        "\n\nWARNING! Parent compartment {} not found in tenancy {}\n\n".format(
            parent_compartment_name,
            config["tenancy"]
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise ResourceWarning("WARNING! - Compartment not found\n")

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client
)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()

if child_compartment is None:
    print(
        "\n\nWARNING! - Child compartment {} not found in parent compartment {}\n".format(
            child_compartment_name,
            parent_compartment_name
        ) +
        "Please try again with a correct name\n\n"
    )
    raise ResourceWarning("WARNING! Compartment not found\n")

# get virtual network data
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name
)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()

if virtual_cloud_network is None:
    print(
        "\n\nWARNING! - Virtual cloud network {} not found in compartment {}\n".format(
            virtual_cloud_network_name,
            child_compartment_name
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise ResourceWarning("WARNING! Virtual cloud network not found\n")

# Finally, get the local peering data
local_peering_gateways = GetLocalPeeringGateway(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    lpg_name
)
local_peering_gateways.populate_local_peering_gateways()

# run through the logic
if lpg_name.upper() == "LIST_ALL_LPGS":
    print(local_peering_gateways.return_all_local_peering_gateways())
else:
    local_peering_gateway = local_peering_gateways.return_local_peering_gateway()
    if local_peering_gateway is None:
        print("\n\nWARNING! Local peering gateway {} not found within virtual cloud network {}\n".format(
            lpg_name,
            virtual_cloud_network_name
        ) +
        "Please try again with a correct name.\n\n"
        )
        raise ResourceWarning("WARNING! - Local peering gateway not found\n")
    if len(option) == 0:
        print(local_peering_gateway)
    elif option == "--OCID":
        print(local_peering_gateway.id)
    elif option == "--NAME":
        print(local_peering_gateway.display_name)
    elif option == "--PEERING-STATUS":
        print(local_peering_gateway.peering_status)
    elif option == "--PEER-ADVERTISED-ROUTE":
        print(local_peering_gateway.peer_advertised_cidr)
    else:
        print(
            "\n\nInvalid option. Valid options are:\n"
            "\t--ocid\t\t\t Print the OCID of the LPG resource\n" +
            "\t--name\t\t\t Print the name of the LPG resource\n" +
            "\t--peering-status\t Print the peering status of the LPG resource\n" +
            "\t--peer-advertised-route\t Print the advertised CIDR route of the LPG resource\n\n" +
            "Please try again with the correct option.\n\n"
        )
        raise ResourceWarning("WARNING! Invalid option\n")


