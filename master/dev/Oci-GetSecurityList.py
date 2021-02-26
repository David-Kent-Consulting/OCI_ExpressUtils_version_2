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

# required OCI modules
from lib.general import copywrite
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.general import get_regions
from lib.routetables import add_route_table
from lib.securitylists import GetNetworkSecurityList
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient


if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetSecurityList : Correct Usage\n\n" +
        "Oci-GetSecurityList.py [parent compartment] [child_compartment] [virtual_network] " +
        "[network security list] [region] [optional argument]\n\n" +
        "Use case example 1 displays all security lists within the virtual cloud network\n" +
        "\tOci-GetSecurityList.py admin_comp auto_comp auto_vcn list_all_security_lists 'us-ashburn-1'\n\n" +
        "Use case examply 2 displays the specified security list within the specified virtual cloud network\n" +
        "\tOci-GetSecurityList.py admin_comp auto_vcn auto_sec 'us-ashburn-1\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("exception! - Incorrect Usage\n")

if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = [] # required for logic to work
if option != "--JSON":
    copywrite()
    sleep(2)

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
security_list_name              = sys.argv[4]
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

# check to see if the security list exists
security_lists = GetNetworkSecurityList(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    security_list_name
)
security_lists.populate_security_lists()

if security_list_name.upper() == "LIST_ALL_SECURITY_LISTS":

    header = [
        "COMPARTMENT",
        "SECURITY LIST",
        "LIFECYCLE STATE",
        "REGION"
    ]
    data_rows = []
    for sec_list in security_lists.return_all_security_lists():
        data_row = [
            child_compartment_name,
            sec_list.display_name,
            sec_list.lifecycle_state,
            region
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    security_list = security_lists.return_security_list()
    if security_list is None:
        print(
            "\n\nWARNING! - Security list {} not found within virtual cloud network{}\n".format(
                security_list_name,
                virtual_cloud_network_name
            ) +
            "Please try again with a correct name.\n\n"
        )
        raise ResourceWarning("WARNING! - Security list not found\n")
    elif option == "--OCID":
        print(security_list.id)
    elif option == "--NAME":
        print(security_list.display_name)
    elif option == "--EGRESS-SECURITY-RULES":
        print(security_list.egress_security_rules)
    elif option == "--INGRESS-SECURITY-RULES":
        print(security_list.ingress_security_rules)
    elif option == "--LIFECYCLE-STATE":
        print(security_list.lifecycle_state)
    elif option == "--JSON":
        print(security_list)

    elif len(option) == 0:

        header = [
        "COMPARTMENT",
        "SECURITY LIST",
        "LIFECYCLE STATE",
        "REGION"
        ]
        data_rows = [[
            child_compartment_name,
            security_list.display_name,
            security_list.lifecycle_state,
            region
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\nSECURITY LIST ID :\t" + security_list.id + "\n")

    else:
        print(
            "\n\nWARNING! - Invalid option. Valid options are:\n" +
            "\t--ocid\t\t\t\tPrint the OCID of the security list resource\n" +
            "\t--name\t\t\t\tPrint the name of the security list resource\n" +
            "\t--egress-security-rules\t\tPrint the egress security rules within the security list\n" +
            "\t--ingress-security-rules\tPrint the ingress security rules within the security list\n" +
            "\t--lifecycle-state\t\tPrint the lifecycle state of the security list resource\n" +
            "\t--json\t\t\t\tPrint all resource data in JSON format and surpress other output\n\n"
            "Please try again with the correct options.\n\n"
        )
        raise RuntimeWarning("WARNING! - Incorrect option\n")
