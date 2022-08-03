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
from tabulate import tabulate
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import warning_beep
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import GetDynamicRouterGateway
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetDynamicRouterGateway.py : Usage\n\n" +
        "Oci-GetDynamicRouterGateway.py [parent compartment] [child compartment] [ virtual cloud network] " +
        "[dynamic router gateway] [region] [optional arguments]\n\n" +
        "Use case example 1 displays all dynamic router gateways for the specified virtual cloud network:\n" +
        "\tOci-GetDynamicRouterGateway.py admin_comp dbs_comp dbs_vcn list_all_drgs 'us-ashburn-1'\n" +
        "Use case example 2 displays the dynamic router gateway for the specified virtual cloud network\n" +
        "\tOci-GetDynamicRouterGateway.py admin_comp vpn_comp vpn0_vcn vpn0_drg 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise ResourceWarning("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
dynamic_router_gateway_name     = sys.argv[4]
region                          = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = [] # required for logic to work
if option != "--JSON":
    copywrite()
    sleep(2)


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

# run through the logic
if sys.argv[4].upper() == "LIST_ALL_DRGS":
    data_rows = []
    header = [
        "COMPARTMENT",
        "DRG",
        "LIFECYCLE STATE"
    ]
    if dynamic_router_gateways.return_all_dynamic_router_gateways() is not None:
        for drg in dynamic_router_gateways.return_all_dynamic_router_gateways():
            data_row = [
                child_compartment_name,
                drg.display_name,
                drg.lifecycle_state
            ]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))
    exit(0)

if dynamic_router_gateway is None:
    print(
        "Dynamic router gateway {} not found within virtual cloud network {}\n".format(
            dynamic_router_gateway_name,
            virtual_cloud_network_name
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Dynamic router gateway not found\n")
elif len(option) == 0:
    
    header = [
        "COMPARTMENT",
        "DRG",
        "LIFECYCLE STATE",
        "DRG ID"
    ]
    data_rows = [[
        child_compartment_name,
        dynamic_router_gateway.display_name,
        dynamic_router_gateway.lifecycle_state,
        dynamic_router_gateway.id
    ]]
    print(tabulate(data_rows, headers = header, tablefmt = "simple"))

elif option == "--OCID":
    print(dynamic_router_gateway.id)
elif option == "--NAME":
    print(dynamic_router_gateway.display_name)
elif option == "--LIFECYCLE-STATE":
    print(dynamic_router_gateway.lifecycle_state)
elif option == "--JSON":
    print(dynamic_router_gateway)
else:
    print(
        "\n\nINVALID OPTION! - Valid options are:\n" +
        "\t--ocid\t\t\tPrints the OCID of the dynamic router gateway resource\n" +
        "\t--name\t\t\tPrintsthe name of the dynamic router gateway resource\n" +
        "\t--lifecycle-state\tPrints the life cycle status of the dynamic router gateway resource\n" +
        "\t--json\t\t\tPrints all resource data in JSON format and supresses other output\n\n" +
        "Please try again with the correct option.\n\n"
    )
    raise ResourceWarning("INVALID OPTION!\n")
