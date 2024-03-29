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
from tabulate import tabulate
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import GetInputOptions
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.securitygroups import GetNetworkSecurityGroup
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient


if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-ListNetworkSecurityGroup.py : Usage\n\n" +
        "Oci-ListNetworkSecurityGroup.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[network security group] [region] [required argument]\n\n" +
        "Use case example 1 lists the network security group rules within the specified network security group:\n" +
        "\tOci-ListNetworkSecurityGroup.py admin_comp bas_comp bas_vcn dmzt01_grp us-ashburn-1 --json\n\n" +
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
if options != "--JSON":
    copywrite()
    sleep(2)

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

# populate the security group rules into a list, then run through the logic
rules = security_groups.return_security_group_rules(security_group.id)

if len(rules) == 0:
    print("\n\nCAUTION! - No rules found in network security group {}\n\n".format(
        security_group_name
    ))
    raise RuntimeWarning("WARNING! - No network security group rules found")
else:
    if options == "--JSON":
        print(rules)
    elif options == "--EGRESS-RULES":
        for item in rules:
            if item.direction == "EGRESS":
                print(item)
    elif options == "--INGRESS-RULES":
        for item in rules:
            if item.direction == "INGRESS":
                print(item)
    else:
        print(
            "\n\nINVALID OPTION OR OPTION MISSING! - Valid options are:\n" +
            "\t--json\t\tPrint all rules in JSON format and suppress other output\n" +
            "\t--egress-rules\t\tPrint all egress rules\n" +
            "\t--ingress-rules\t\tPrint all ingress rules\n\n" +
            "Please try again with the correct option.\n"
        )
        raise RuntimeWarning("INVALID OPTION")