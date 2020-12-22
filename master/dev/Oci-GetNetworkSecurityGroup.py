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
from lib.securitygroups import GetNetworkSecurityGroup
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import UpdateSubnetDetails

if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetNetworkSecurityGroup.py : Usage\n\n" +
        "Oci-GetNetworkSecurityGroup.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[network security group] [region] [optional argument]\n\n" +
        "Use case example 1 lists all network security groups within the specified virtual cloud network:\n" +
        "\tOci-GetNetworkSecurityGroup.py admin_comp auto_comp auto_vcn list_all_security_groups_in_vcn 'us-ashburn-1'\n\n" +
        "Use case example 2 lists just the specific network security group details:\n" +
        "\tOci-GetNetworkSecurityGroup.py admin_comp auto_comp auto_vcn auto_grp us-ashburn-1\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Incorrect usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
security_group_name         = sys.argv[4]
region                      = sys.argv[5]
if len(sys.argv) == 7:
    options = sys.argv[6].upper()
else:
    options = [] # required for logic to work

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

# get security group data
security_groups = GetNetworkSecurityGroup(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    security_group_name
)
security_groups.populate_security_groups()
security_group = security_groups.return_security_group()
error_trap_resource_not_found(
    security_group,
    "Unable to find security group " + security_group_name + " within virtual cloud network " + virtual_cloud_network_name
)

# run through the logic
if len(options) == 0:
    print(security_group)
elif options == "--OCID":
    print(security_group.id)
elif options == "--NAME":
    print(security_group.display_name)
elif options == "--LIFECYCLE-STATE":
    print(security_group.lifecycle_state)
elif options == "--VIRTUAL-CLOUD-NETWORK":
    print(security_group.vcn_id)
else:
    print(
        "\n\nINVALID OPTION! - Valid options are:\n" +
        "\t--ocid\t\t\t\tPrints the OCID of the network security group resource\n" +
        "\t--name\t\t\t\tPrints the name of the network security group resource\n" +
        "\t--lifecycle-state\t\tPrints the lifecycle state of the network security group resource\n" +
        "\t--virtual-cloud-network\t\tPrints the OCID of the virtual cloud network associated with the network security group\n\n" +
        "Please try again with a correct option.\n\n"
    )
    raise RuntimeWarning("WARNING! - Invalid option")

