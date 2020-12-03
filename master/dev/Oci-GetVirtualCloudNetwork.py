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
from oci import config
import oci
from lib.vcns import GetVirtualCloudNetworks
from lib.vcns import add_virtual_cloud_network
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments

option = [] # must have a len() == 0 for subsequent logic to work


'''
MUST ADD REGION AS ARGV
'''

if len(sys.argv) < 5 or len(sys.argv) > 6: # ARGS PLUS COMMAND
    print(
        "\n\nOci-GetVirtualCloudNetwork.py : Correct Usage\n\n" +
        "Oci-GetVirtualCloudNetwork.py [parent compartment name] [child compartment name] [vcn name] [region] [optional argument]\n\n" +
        "Use case example 1 prints details of the provided virtual cloud network within the specified child compartment\n\n" +
        "\tOci-GetVirtualNetwork.py admin_comp auto_comp auto_vcn 'us-ashburn-1'\n\n" +
        "Use case example 2 prints all virtual cloud networks found within the child compartment\n\n" +
        "\tOci-GetVirtualCloudNetwork.py admin_comp auto_comp list_all_vcns_in_compartment 'us-ashburn-1'\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning(
        "EXCEPTION! Incorrect Usage"
    )

if len(sys.argv) == 6:
    option = sys.argv[5]
parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
region                      = sys.argv[4]

# initialize the environment

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
config["region"] = region

# this initiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# this initiates the method VirtualCloudNetworks from the API
network_client = oci.core.VirtualNetworkClient(config)
# We create the method my_compartments from the DKC API 
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()

parent_compartment = parent_compartments.return_parent_compartment()
if parent_compartment is None:
    print("\n\nEXCEPTION! - Parent compartment {} not found in tenancy {}.\n\n".format(
        parent_compartment_name, config["tenancy"]
        ) +
        "Please try again with a correct parent compartment name.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Parent Compartment Not Found\n")
else:
    # get the compartment resources
    child_compartments = GetChildCompartments(
        parent_compartments.return_parent_compartment().id,
        child_compartment_name,
        identity_client
    )
    child_compartments.populate_compartments()
    child_compartment = child_compartments.return_child_compartment()
    if child_compartment is None:
        print("\n\nEXCEPTION! - Child compartment {} not found in parent compartment {}\n\n".format(
            child_compartment_name, parent_compartment_name
            ) +
            "Please try again with a correct child compartment name"
             )
        raise RuntimeError("EXCEPTION! - Child Compartment Not Found\n")

# now get the virtual network resources
virtual_networks = GetVirtualCloudNetworks(network_client, child_compartment.id, virtual_cloud_network_name)
virtual_networks.populate_virtual_cloud_networks()

# run through the logic and return the requested results
if virtual_cloud_network_name.upper() == "LIST_ALL_VCNS_IN_COMPARTMENT":
    print(virtual_networks.return_all_virtual_networks())
else:
    virtual_cloud_network = virtual_networks.return_virtual_cloud_network()
    if virtual_cloud_network is None:
        print("\n\nVirtual cloud network {} not found in child compartment {}\n\n".format(
            virtual_cloud_network_name,
            child_compartment_name
            ) +
            "Please try again with a correct virtual cloud network name.\n"
        )
        raise RuntimeError("EXCEPTION! - Virtual Cloud Network Not Found")
    elif option == "--ocid":
        print(virtual_cloud_network.id)
    elif option == "--name":
        print(virtual_cloud_network.display_name)
    elif option == "--cidr-block":
        print(virtual_cloud_network.cidr_block)
    elif option == "--domain-name":
        print(virtual_cloud_network.vcn_domain_name)
    elif option == "--defaults":
        print("\n\nOption --defaults to be available in a later release.\n" +
        "Printing all VCN details for now.\n\n")
        print(virtual_cloud_network)
    elif len(option) == 0:
        print(virtual_cloud_network)
    else:
        print("\n\nInvalid option. Valid options are:\n" +
            "\t--ocid\t\t : the OCID of the VCN resource\n" +
            "\t--name\t\t : the name of the VCN resource\n" +
            "\t--cidr-block\t : The CIDR IP address range of the VCN\n" +
            "\t--domain-name\t : the fully qualified domain name of the VCN\n" +
            "\t--defaults\t : the default settings for DHCP, route table, and security list\n\n" +
            "Please try again with a correct option.\n\n")
        raise RuntimeError("EXCEPTION! Invalid Option")
