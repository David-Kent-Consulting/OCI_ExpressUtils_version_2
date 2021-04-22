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
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.subnets import add_subnet
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import CreateSubnetDetails

option = [] # must have a len() == 0 for subsequent logic to work


if len(sys.argv) < 6 or len(sys.argv) > 7: # ARGS PLUS COMMAND
    print(
        "\n\nOci-GetVirtualCloudSubNetwork.py : Correct Usage\n\n" +
        "Oci-GetVirtualCloudSubNetwork.py [parent compartment name] [child compartment name] [vcn name]" +
        "[subnet name] [region] [optional argument]\n\n" +
        "Use case example 1 lists all subnets that are members of the VCN\n\n"+
        "\tOci-GetVirtualCloudSubnetwork.py admin_comp dr_comp dr_vcn list_all_subnetworks 'us-phoenix-1'\n\n"
        "Use case example 2 gets the virtual cloud subnetwork within the specified virtual cloud network\n\n" +
        "\tOci-GetVirtualCloudSubNetwork.py admin_comp auto_comp auto_vcn auto_sub01 autosub01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning(
        "EXCEPTION! Incorrect Usage"
    )

if len(sys.argv) == 7:
    option = sys.argv[6].upper()
if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching and validating tenancy resource data......\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
subnet_name                     = sys.argv[4]
region                          = sys.argv[5]

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

# Get the subnets
subnets = GetSubnet(network_client, child_compartment.id, virtual_cloud_network.id, subnet_name)
subnets.populate_subnets()

# run through the logic

if subnet_name.upper() == "LIST_ALL_SUBNETWORKS":

    header = [
        "COMPARTMENT",
        "VCN",
        "VCN CIDR",
        "SUBNETWORK",
        "CIDR",
        "LIFECYCLE STATE",
        "REGION"
    ]
    data_rows = []
    if subnets.return_all_subnets() is not None:
        for subnet in subnets.return_all_subnets():
            data_row = [
                child_compartment_name,
                virtual_cloud_network.display_name,
                virtual_cloud_network.cidr_block,
                subnet.display_name,
                subnet.cidr_block,
                subnet.lifecycle_state,
                region
            ]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    subnet = subnets.return_subnet()
    error_trap_resource_not_found(
        subnet,
        "Subnetwork " + subnet_name + " not found within virtual cloud network " + virtual_cloud_network_name + " in region " + region
    )
    '''
    Get other resource data associated with subnet using the OCI network client.
    The codebase by design supports only 1 security list assignment per subnet and thus,
    we only report the 1st security list returned by network_client.get_security_list
    '''
    dhcp_options      = network_client.get_dhcp_options(dhcp_id = subnet.dhcp_options_id).data
    route_table       = network_client.get_route_table(rt_id = subnet.route_table_id).data
    security_list   = network_client.get_security_list(security_list_id = subnet.security_list_ids[0]).data

    if option == "--OCID":
        print(subnet.id)
    elif option == "--NAME":
        print(subnet.display_name)
    elif option == "--DOMAIN-NAME":
        print(subnet.subnet_domain_name)
    elif option == "--PROHIBIT_PUBLIC_IP_ADDRESSES":
        print(subnet.prohibit_public_ip_on_vnic)
    elif option == "--LIFECYCLE-STATE":
        print(subnet.lifecycle_state)
    elif option == "--JSON":
        print(subnet)
    elif len(sys.argv) == 6:

        header = [
            "COMPARTMENT",
            "VCN",
            "VCN CIDR",
            "SUBNETWORK",
            "FQDN",
            "PROHIBIT PUB IPs",
            "CIDR",
            "LIFECYCLE STATE",
            "REGION"
        ]
        data_rows = [[
            child_compartment_name,
            virtual_cloud_network.display_name,
            virtual_cloud_network.cidr_block,
            subnet.display_name,
            subnet.subnet_domain_name,
            subnet.prohibit_public_ip_on_vnic,
            subnet.cidr_block,
            subnet.lifecycle_state,
            region
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\nSUBNET ID :\t\t\t" + subnet.id)
        print("DHCP OPTIONS ASSIGNMENT :\t" + dhcp_options.display_name)
        print("ROUTE TABLE ASSIGNMENT :\t" + route_table.display_name)
        print("SECURITY LIST ASSIGNMENT :\t" + security_list.display_name)

    else:
        print(
            "\n\nIncorrect options. Correct options are:\n" +
            "\t--ocid\t\t\t\tThe OCID of the subnet resource\n" +
            "\t--name\t\t\t\tThe name of the subnet resource\n" +
            "\t--prohibit_public_ip_addresses\tReturns False if public IP addresses are allowed, otherwise it returns True\n" +
            "\t--lifecycle-state\t\tThe lifecycle state of the subnet resource\n" +
            "\t--json\t\t\t\tPrints all resource data in JSON format and surpresses other output\n\n" +
            "Please try again with a correct option.\n\n"
        )
        raise RuntimeWarning("WARNING! Invalid option\n")