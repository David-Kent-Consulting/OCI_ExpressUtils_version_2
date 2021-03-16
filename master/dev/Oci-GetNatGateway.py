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
from lib.general import warning_beep
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import delete_nat_gateway
from lib.gateways import GetNatGateway
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient


if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetNetGateway.py : Usage\n\n" +
        "\n\nOci-GetNatGateway.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[nat gateway] [region] [optional argument]\n\n" +
        "Use case example 1 displays all NAT tables within the virtual cloud network:\n" +
        "\tOci-GetNatGateway.py admin_comp bas_comp bas_vcn list_all_nat_gateways 'us-ashburn-1'\n" +
        "Use case example 2 displays the NAT gateway resource within the virtual cloud network.\n" +
        "\tOci-GetNatGateway.py admin_comp auto_comp auto_vcn auto_ngw 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RecursionError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
nat_gateway_name                = sys.argv[4]
region                          = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = [] # necessary for logic to work
if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFletching and validating tenancy resource data......\n")

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

# Get the NAT gateway resources
nat_gateways = GetNatGateway(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    nat_gateway_name
)
nat_gateways.populate_nat_gateways()
nat_gateway = nat_gateways.return_nat_gateway()

# run through the logic

if nat_gateway_name.upper() == "LIST_ALL_NAT_GATEWAYS" and len(sys.argv) == 6:
    
    header = [
        "COMPARTMENT",
        "VCN",
        "NAT\nGATEWAY",
        "LIFECYCLE\nSTATE",
        "REGION"
    ]
    data_rows = []
    if nat_gateways.return_all_nat_gateways() is not None:
        for ngw in nat_gateways.return_all_nat_gateways():
            data_row = [
                child_compartment_name,
                virtual_cloud_network_name,
                ngw.display_name,
                ngw.lifecycle_state,
                region
            ]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    if nat_gateway is None:
        print(
            "\n\nNAT gateway {} not found within virtual cloud network {}\n\n".format(
                nat_gateway_name,
                virtual_cloud_network_name
            ) +
            "Please try again with a correct name.\n\n"
        )
        raise RuntimeWarning("WARNING! - NAT Gateway not found\n")
    else:
        if len(option) == 0:

            header = [
                "COMPARTMENT",
                "NAT GATEWAY",
                "PUBLIC IP ADDRESS",
                "BLOCK TRAFFIC",
                "LIFECYCLE STATE",
                "REGION"
            ]
            data_rows = [[
                child_compartment_name,
                nat_gateway.display_name,
                nat_gateway.nat_ip,
                nat_gateway.block_traffic,
                nat_gateway.lifecycle_state,
                region
            ]]
            print(tabulate(data_rows, headers = header, tablefmt = "simple"))
            print("\n\nNAT GATEWAY ID :\t" + nat_gateway.id + "\n\n")

        elif option == "--OCID":
            print(nat_gateway.id)
        elif option == "--NAME":
            print(nat_gateway.display_name)
        elif option == "--NAT-IP":
            print(nat_gateway.nat_ip)
        elif option == "--LIFECYCLE-STATE":
            print(nat_gateway.lifecycle_state)
        elif option == "--JSON":
            print(nat_gateway)
        else:
            print(
                "\n\nInvalid option. Valid options include:\n\n" +
                "\t--ocid\t\t\tPrints the OCID of the NAT gateway resource\n" +
                "\t--name\t\t\tPrints the NAT Gateway name\n" +
                "\t--nat-ip\t\tPrints the NAT gateway's public IP address\n" +
                "\t--lifecycle-state\tPrints the lifecycle state of the NAT gateway resource\n" +
                "\t--json\t\t\tPrint all resource data in JSON format and surpress other output\n\n" +
                "Please try again with a correct option\n\n"
            )
    