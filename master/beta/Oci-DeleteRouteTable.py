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
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.routetables import delete_route_table
from lib.routetables import GetRouteTable
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7: # ARGS PLUS COMMAND
    print(
        "\n\nOci_DeleteRouteTable.py : Correct Usage\n\n" +
        "Oci-DeleteRouteTable.py [parent compartment name] [child compartment name] [vcn name]" +
        "[route table name] [region] [optional argument]\n\n" +
        "Use case example deletes the route table within the specified virtual cloud network without prompting the user\n\n" +
        "\tOci-DeleteRouteTable admin_comp web_comp web_vcn web_rtb 'us-ashburn-1' --force\n\n" +
        "Remove the --force option to be prompted prior to removal of the route table resource.\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

if len(sys.argv) == 7:
    option = sys.argv[6]
else:
    option = [] # necessary for logic to work
parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
route_table_name                = sys.argv[4]
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

# Check to see if the route table exists
route_tables = GetRouteTable(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    route_table_name
)
route_tables.populate_route_tables()
route_table = route_tables.return_route_table()

# Delete the route table
if route_table is None:
    print(
        "\n\nWARNING! - Route table {} not found within child compartment {}\n".format(
            route_table_name,
            child_compartment_name
        ) +
        "Please try again with a correct route table name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Route table not found\n")
elif option == "--force":
    results = delete_route_table(
        network_client,
        route_table.id
    )
    if results is None:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR\n")
    else:
        print("Route table {} deleted from virtual cloud network {}\n".format(
            route_table_name,
            virtual_cloud_network_name
        ))
elif len(option) == 0:
    warning_beep(6)
    print("Enter YES to delete route table {} from virtual network {}, or any other key to abort : ".format(
        route_table_name,
        virtual_cloud_network_name
    ))
    if "YES" == input():
        results = delete_route_table(
            network_client,
            route_table.id)
        if results is None:
            raise RuntimeError("EXCEPTION! - UNKNOWN ERROR\n")
        else:
            print("Route table {} deleted from virtual cloud network {}\n".format(
                route_table_name,
                virtual_cloud_network_name
            ))
    else:
        print("Delete of route table {} aborted by user\n".format(route_table_name))
else:
    print(
        "\n\nInvalid option. The only valid option is --force\n" +
        "Please try again.\n"
    )
    raise RuntimeWarning("WARNING! - Invalid option\n")