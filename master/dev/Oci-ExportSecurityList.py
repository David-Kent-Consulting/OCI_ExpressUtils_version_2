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
from lib.general import make_sure_export_file_is_not_zero_bytes
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.routetables import add_route_table
from lib.securitylists import prepare_csv_record
from lib.securitylists import export_security_list_rules_to_csv
from lib.securitylists import GetNetworkSecurityList
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient

if len(sys.argv) != 6:
    print(
        "\n\nOci-ExportSecurityList : Correct Usage\n\n" +
        "Oci-ExportSecurityList.py [parent compartment] [child_compartment] [virtual_network] " +
        "[network security list] [region]\n\n" +
        "Use case example exports all security list rules for the specified security list to CSV format.\n" +
        "\tOci-ExportSecurityList.py admin_comp auto_comp auto_vcn auto_sec 'us-ashburn-1'\n\n" +
        "The format of the CSV is <field1>;<field2>;.......<last field><CR>\n" +
        "The CSV file is named <security list name>_rules.csv and includes a header file that describes each field.\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("exception! - Incorrect Usage\n")

if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = [] # required for logic to work

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
security_list_name              = sys.argv[4]
region                          = sys.argv[5]
security_rule_export_file = security_list_name + "_rules.csv" # this will be the name of the exported CSV file

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

# check to see if the security list exists
security_lists = GetNetworkSecurityList(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    security_list_name
)
security_lists.populate_security_lists()
security_list = security_lists.return_security_list()
error_trap_resource_not_found(
    security_list_name,
    "Security list " + security_list_name + " not found within virtual cloud network " + virtual_cloud_network_name
)

# Get the rules
ingress_rules = security_list.ingress_security_rules
egress_rules = security_list.egress_security_rules
security_rules = []
for rule in ingress_rules:
    security_rules.append(rule)
for rule in egress_rules:
    security_rules.append(rule)

# export the rules
export_security_list_rules_to_csv(
    security_rule_export_file,
    security_rules,
    ";")

# Now check to make sure the file just created is not zero bytes, then exit accordingly
