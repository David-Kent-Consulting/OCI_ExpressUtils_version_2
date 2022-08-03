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

# required DKC modules
from lib.general import copywrite
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.routetables import GetRouteTable
from lib.securitylists import GetNetworkSecurityList
from lib.subnets import add_subnet
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import CreateSubnetDetails

copywrite()
sleep(2)
if len(sys.argv) != 11: # ARGS PLUS COMMAND
    print(
        "\n\nOci-AddVirtualCloudSubNetwork.py : Correct Usage\n\n" +
        "Oci-AddVirtualCloudSubNetwork.py [parent compartment name] [child compartment name] [vcn name]" +
        "[subnet name] [subnet dns name] [subnet cidr] [prohibit public IP address (True/False)]" +
        "[route table name] [security list name] [region]\n\n" +
        "Use case example adds virtual cloud subnetwork within the specified virtual cloud network\n\n" +
        "\tOci-AddVirtualCloudSubNetwork.py admin_comp auto_comp auto_vcn auto_sub01 autosub01 '10.1.1.0/24' \\ \n" +
        "\tfalse auto_rtb auto_sec 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning(
        "EXCEPTION! Incorrect Usage\n"
    )

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
subnet_name                     = sys.argv[4]
subnet_dns_name                 = sys.argv[5]
subnet_cidr                     = sys.argv[6]
prohibit_pub_ip_addresses       = sys.argv[7]
route_table_name                = sys.argv[8]
security_list_name              = sys.argv[9]
region                          = sys.argv[10]

# set boolean value for prohibit_pub_ip_addresses based on string input, or abort if invalid entry
if prohibit_pub_ip_addresses.upper() == "TRUE":
    prohibit_pub_ip_addresses = True
elif prohibit_pub_ip_addresses.upper() == "FALSE":
    prohibit_pub_ip_addresses = False
else:
    print(
        "\n\nEXCEPTION! - Valid input for prohibit_pub_ip_addresses must either be 'true' or 'false'.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

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

# Check to see if the subnet exists
subnets = GetSubnet(network_client, child_compartment.id, virtual_cloud_network.id, subnet_name)
subnets.populate_subnets()
subnet = subnets.return_subnet()
if subnet is not None:
    print(
        "\n\nWARNING! - Cloud subnetwork {} already exists within compartment {}.\n".format(
            subnet_name,
            child_compartment_name
        ) +
        "Duplicate names are not supported by this utility. Please try again with\n" +
        "a unique cloud subnetwork name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Subnetwork name already present.\n")
else:
    # create the subnetwork

    # Get the route table
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
            "\n\nWARNING! - Route table {} not found in compartment {}\n".format(
                route_table_name,
                child_compartment_name
            ) +
            "Please try again with a correct route table name.\n\n"
        )
        raise RuntimeWarning("WARNING! Route table not found\n")
    security_lists = GetNetworkSecurityList(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        security_list_name
    )
    # get the security list
    security_lists.populate_security_lists()
    security_list = security_lists.return_security_list()
    if security_list is None:
        print(
            "\n\nWARNING! Security list {} not found in compartment {}\n".format(
                security_list_name,
                child_compartment_name
            ) +
            "Please try again with a correct security list name.\n\n"
        )
        raise RuntimeWarning("WARNING! - Security list not found\n")
    results = add_subnet(
        network_client,
        subnet_cidr,
        child_compartment.id,
        subnet_name,
        subnet_dns_name,
        prohibit_pub_ip_addresses,
        route_table.id,
        security_list.id,
        virtual_cloud_network.id
    )
    if results is None:
        raise RuntimeError("ECEPTION! - UNKNOWN ERROR\n")
    else:
        print(results)