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
from lib.general import error_trap_resource_not_found
from lib.general import GetInputOptions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.routetables import GetRouteTable
from lib.securitylists import GetNetworkSecurityList
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import UpdateSubnetDetails


if len(sys.argv) == 2 and sys.argv[1].upper() == "--HELP":
    print(
        "\n\nOci-UpdateVirtualCloudSubNetwork.py [parent compartment] [child compartment] [virtual cloud network] \\\n" +
        "[subnet] [region] [--dhcp-options] <value> [--display-name] <value> [--route-table] [value] [--security-list] <value> \n\n" +
        "\t--dhcp-options:[future feature]\t\tThe name of the DHCP options resource to apply to the subnetwork\n" +
        "\t--display-name:\t\t\t\tThe new display name to apply to the the subnetwork\n" +
        "\t--route-table:\t\t\t\tThe name of the route table to apply to the subnetwork\n" +
        "\t--security-list:\t\t\tThe name of the security list to apply to the subnetwork\n"
    )
    exit(0)
elif len(sys.argv) < 8 or len(sys.argv) > 14:
    print(
        "\n\nOciUpdateVirtualCloudSubnetwork.py : Usage\n\n" +
        "Oci-UpdateVirtualCloudSubnetwork.py [parent compartment] [child_compartment] [virtual cloud network] \\\n" +
        "[subnetwork] [region] [option arguments with inputs]\n\n" +
        "Use case example updates the subnet and assigns the specified route table to it:\n" +
        "\tOci-UpdateVirtualCloudSubnetwork.py admin_comp auto_comp auto_vcn auto_sub 'us-ashburn-1' --route-table auto_rtb\n" +
        "Run 'Oci-UpdateVirtualCloudSubnetwork --help' for a list of available options for this utility.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
subnet_name                 = sys.argv[4]
region                      = sys.argv[5]


# populate the argument list from the method GetInputOptions at position 6 in sys.argv,
# which is the starting position to get optional arguments.
argument_list               = GetInputOptions(sys.argv)
argument_list.populate_input_options(6)
# print(argument_list.options_list_with_input)


# instiate the environment
config = from_file() # gets ~./.oci/config and reads to the object
config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources





# get parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Unable to find parent compartment " + parent_compartment_name + " within tenancy " + config["tenancy"]
)

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Unable to find child compartment " + child_compartment_name + " in parent compartment " + parent_compartment_name
)

# get virtual cloud network data
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
error_trap_resource_not_found(
    virtual_cloud_network,
    "Unable to find virtual cloud network " + virtual_cloud_network_name + " in child compartment " + child_compartment_name
)

# get subnetwork data
subnets = GetSubnet(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    subnet_name
    )
subnets.populate_subnets()
subnet = subnets.return_subnet()
error_trap_resource_not_found(
    subnet,
    "Unable to find subnetwork " + subnet_name + " within virtual cloud network " + virtual_cloud_network_name
)

'''
This part of the logic will now test for each option using the method argument_list that was instiated from
lib.general.GetInputOptions. If the option is found in the list, the list for that item is appended, if not,
the list value is left as null. This will later be used to build subnet_details, which will later be applied
by calling network_client.update_subnet
'''

# set all expected settings to pass to UpdateSubnetDetails
dhcp_options_id = None 
display_name = None
route_table_id = None
security_list_ids = []

if "--DHCP-OPTIONS" in argument_list.options_list_with_input:
    #dhcp_options = argument_list.return_input_option_data("--DHCP-OPTIONS")
    print("DHCP Options support in a future release, use the OCI console to manage this feature.\n")
    exit(0)

if "--DISPLAY-NAME" in argument_list.options_list_with_input:
    display_name = argument_list.return_input_option_data("--DISPLAY-NAME")

if "--ROUTE-TABLE" in argument_list.options_list_with_input:
    route_table_name = argument_list.return_input_option_data("--ROUTE-TABLE")
    route_tables = GetRouteTable(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        route_table_name
    )
    route_tables.populate_route_tables()
    route_table = route_tables.return_route_table()
    error_trap_resource_not_found(
        route_table,
        "Route table " + route_table_name + " not found in virtual cloud network " + virtual_cloud_network_name
    )
    route_table_id = route_table.id

if "--SECURITY-LIST" in argument_list.options_list_with_input:
    security_list_name = argument_list.return_input_option_data("--SECURITY-LIST")
    security_lists = GetNetworkSecurityList(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        security_list_name
    )
    security_lists.populate_security_lists()
    security_list = security_lists.return_security_list()
    error_trap_resource_not_found(
        security_list,
        "Security list " + security_list_name + " not found within virtual cloud network " + virtual_cloud_network_name
    )
    security_list_ids.append(security_list.id)

# create the method subnet_details
# Manage values for options when not supplied by the user
if display_name is None:
    display_name = subnet_name
if len(security_list_ids) == 0:
    for item in subnet.security_list_ids: # must apply as a list
        security_list_ids.append(item)
if route_table_id is None:
    route_table_id = subnet.route_table_id

subnet_details = UpdateSubnetDetails(
    dhcp_options_id = dhcp_options_id,
    display_name = display_name,
    route_table_id = route_table_id,
    security_list_ids = security_list_ids
)


# Apply changes to the subnet
results = network_client.update_subnet(
    subnet_id = subnet.id,
    update_subnet_details = subnet_details
)
if results is not None:
    print(
        "Subnet changes successfully applied to {}\n\n{}".format(subnet_name, subnet_details)
    )