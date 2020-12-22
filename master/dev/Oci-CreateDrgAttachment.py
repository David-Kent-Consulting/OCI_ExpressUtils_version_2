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
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import GetInputOptions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import attach_drg_to_vcn
from lib.gateways import GetDrgAttachment
from lib.gateways import GetDynamicRouterGateway
from lib.routetables import GetRouteTable
from lib.securitylists import GetNetworkSecurityList
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import CreateDrgAttachmentDetails

if len(sys.argv) != 8:
    print(
        "\n\nOci-CreateDrgAttachment.py : Usage\n\n" +
        "Oci-CreateDrgAttachment.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[dynamic router gateway] [route table] [DRG attachment name] [region]\n\n" +
        "Use case example attaches the  dynamic router gateway to the specified virtual cloud network:\n" +
        "\tOci-CreateDrgAttachment.py admin_comp vpn_comp vpn0_vcn vpn0_drg vpn0_rtb vpn0_drg_attachment 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
dynamic_router_gateway_name = sys.argv[4]
route_table_name            = sys.argv[5]
drg_attachment_name         = sys.argv[6]
region                      = sys.argv[7]

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

# get the route table data
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
    "Unable to find route table " + route_table_name + " within virtual cloud network " + virtual_cloud_network_name
)

# get the dynamic router data
dynamic_router_gateways = GetDynamicRouterGateway(
    network_client,
    child_compartment.id,
    dynamic_router_gateway_name
)
dynamic_router_gateways.populate_dynamic_router_gateways()
dynamic_router_gateway = dynamic_router_gateways.return_dynamic_router_gateway()
error_trap_resource_not_found(
    dynamic_router_gateway,
    "Unable to find dynamic router gateway " + dynamic_router_gateway_name + " within virtual cloud network " + virtual_cloud_network_name
)

# check to see if the DRG attachment exists, and if so, then abort, otherwise, create the DRG attachment
drg_attachments = GetDrgAttachment(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    drg_attachment_name
)
drg_attachments.populate_drg_attachments()
drg_attachment = drg_attachments.return_drg_attachment()

error_trap_resource_found(
    drg_attachment,
    "DRG attachment " + drg_attachment_name + " already attached to virtual cloud network " + virtual_cloud_network_name
)

def error_trap_unable_to_create_resource(
    item,
    description):

    if item is None:
        print(
            "\n\nEXCEPTION! - " + description + "\n\n"
        )
        raise RuntimeError("EXPECTION! - UNKNOWN ERROR\n")

# create the resource
results = None
results = attach_drg_to_vcn(
    network_client,
    CreateDrgAttachmentDetails,
    drg_attachment_name,
    dynamic_router_gateway.id,
    route_table.id,
    virtual_cloud_network.id
)

error_trap_unable_to_create_resource(
    results,
    "Unable to create DRG attachment of dynamic router gateway " + dynamic_router_gateway_name + " to virtual cloud network " + virtual_cloud_network_name
)

print(results)