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
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import GetInputOptions
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.gateways import delete_drg_attachment
from lib.gateways import GetDrgAttachment
from lib.gateways import GetDynamicRouterGateway
from lib.routetables import GetRouteTable
from lib.securitylists import GetNetworkSecurityList
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import CreateDrgAttachmentDetails

copywrite()
sleep(2)
if len(sys.argv) < 7 or len(sys.argv) > 8:
    print(
        "\n\nOci-GetDrgAttachment.py : Usage\n\n" +
        "Oci-DGetDrgAttachment.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[dynamic router gateway] [DRG attachment name] [region] [optional argument]\n\n" +
        "Use case example 1 gets all dynamic router gateway attachments from the specified virtual cloud network:\n" +
        "\tOci-GetDrgAttachment.py admin_comp vpn_comp vpn0_vcn vpn0_drg list_all_drg_attachments 'us-ashburn-1'\n"
        "Use case example 2 gets the dynamic router gateway attachment from the specified virtual cloud network:\n" +
        "\tOci-GetDrgAttachment.py admin_comp vpn_comp vpn0_vcn vpn0_drg vpn0_drg_attachment 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
dynamic_router_gateway_name = sys.argv[4]
drg_attachment_name         = sys.argv[5]
region                      = sys.argv[6]
if len(sys.argv) == 8:
    options = sys.argv[7].upper()
else:
    options = [] # required for logic to work

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

# check to see if the DRG attachment exists, and if so, then abort, otherwise, delete the DRG attachment
drg_attachments = GetDrgAttachment(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    drg_attachment_name
)
drg_attachments.populate_drg_attachments()

# run through the logic
if sys.argv[5].upper() == "LIST_ALL_DRG_ATTACHMENTS":
    print(drg_attachments.drg_attachments)
    exit(0)

drg_attachment = drg_attachments.return_drg_attachment()
error_trap_resource_not_found(
    drg_attachment,
    "DRG attachment " + drg_attachment_name + " currently not associated with virtual cloud network " + virtual_cloud_network_name
)
if len(options) == 0:
    print(drg_attachment)
elif options == "--OCID":
    print(drg_attachment.id)
elif options == "--NAME":
    print(drg_attachment.display_name)
elif options == "--LIFECYCLE-STATE":
    print(drg_attachment.lifecycle_state)
elif options == "--ROUTE-TABLE":
    print("Dynamic router gateway attachment {} is associated with router table OCID {}\n".format(
        drg_attachment_name,
        drg_attachment.route_table_id
    ))
elif options == "--VIRTUAL-CLOUD-NETWORK":
    print("Dynamic router gateway attachment {} is assocated with virtual cloud network OCID {}\n".format(
        drg_attachment_name,
        drg_attachment.vcn_id
    ))
else:
    print(
        "\n\nINVALID OPTION! Valid options are:\n" +
        "\t--ocid\t\t\t\tPrints the OCID of the DRG attachment resource\n" +
        "\t--name\t\t\t\tPrints the name of the DRG attachment resource\n" +
        "\t--lifecycle-state\t\tPrints the lifecycle state of the DRG attachment resource\n" +
        "\t--route-table\t\t\tPrints the OCID of the route table associated with the DRG attachment resource\n" +
        "\t--virtual-cloud-network\t\tPrints the OCID of the virtual cloud network associated with the DRG attachment resource\n\n" +
        "Please try again with the correct option\n\n"
    )
    raise RuntimeWarning("INVALID OPTION\n")