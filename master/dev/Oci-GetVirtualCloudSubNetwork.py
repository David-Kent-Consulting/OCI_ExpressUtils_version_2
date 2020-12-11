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
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.subnets import add_subnet
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks
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
parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
subnet_name                     = sys.argv[4]
region                          = sys.argv[5]

# instiate dict and method objects
config = from_file() # gets ~./.oci/config and reads to the object
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
    print(subnets.return_all_subnets())
else:
    subnet = subnets.return_subnet()
    if subnet is None:
        print(
            "\n\nCloud subnetwork {} not found within virtual cloud network {}\n".format(
                subnet_name,
                virtual_cloud_network_name
            ) +
            "Please try again with a correct subnetwork name.\n\n"
        )
        raise RuntimeWarning("WARNING! Subnet not found\n")
    elif option == "--OCID":
        print(subnet.id)
    elif option == "--NAME":
        print(subnet.display_name)
    elif option == "--CIDR-BLOCK":
        print(subnet.cidr_block)
    elif option == "--DOMAIN-NAME":
        print(subnet.subnet_domain_name)
    elif option == "--PROHIBIT_PUBLIC_IP_ADDRESSES":
        print(subnet.prohibit_public_ip_on_vnic)
    elif option == "--LIFECYCLE-STATE":
        print(subnet.lifecycle_state)
    elif option == "--DEFAULTS":
        print("\n\nOption --defaults to be available in a later release.\n" +
        "Printing all subnet details for now.\n\n")
        print(subnet)
    elif len(option) == 0:
        print(subnet)
    else:
        print(
            "\n\nIncorrect options. Correct options are:\n" +
            "\t--ocid\t\t : The OCID of the subnet resource\n" +
            "\t--name\t\t : The name of the subnet resource\n" +
            "\t--cidr-block\t : The CIDR of the subnet resource\n" +
            "\t--domain-name\t : The fully qualified domain name of the subnet resource\n" +
            "\t--prohibit_public_ip_addresses\t: Returns False if public IP addresses are allowed, otherwise it returns True\n" +
            "\t--lifecycle-state\t : The lifecycle state of the subnet resource\n" +
            "\t--defaults\t : The default settings for the subnet resource\n\n" +
            "Please try again with a correct option.\n\n"
        )
        raise RuntimeWarning("WARNING! Invalid option\n")