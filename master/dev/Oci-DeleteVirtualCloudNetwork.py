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
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.vcns import GetVirtualCloudNetworks
from lib.vcns import delete_virtual_cloud_network

# required OCI modules
from oci import config
import oci


option = [] # must have a len() == 0 for subsequent logic to work


copywrite()
sleep(2)
if len(sys.argv) < 5 or len(sys.argv) > 6: # ARGS PLUS COMMAND
    print(
        "\n\nOci-DeleteVirtualCloudNetwork.py : Correct Usage\n\n" +
        "Oci-DeleteVirtualCloudNetwork.py [parent compartment name] [child compartment name] [vcn name] [region] [optional argument]\n\n" +
        "Use case example 1 deletes the virtual cloud network within the specified child compartment without prompting the user\n\n" +
        "\tOci-DeleteVirtualNetwork.py admin_comp auto_comp auto_vcn autovcn 'us-ashburn-1' --force\n\n" +
        "Remove the --force option to be prompted prior to deletion of the virtual cloud network.\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning(
        "EXCEPTION! Incorrect Usage"
    )
if len(sys.argv) == 6:
    option = sys.argv[5]
parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
region                          = sys.argv[4]

# initialize the environment

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
identity_client = oci.identity.IdentityClient(config)
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
    print("\n\nWARNING! - Parent compartment {} not found in tenancy {}.\n\n".format(
        parent_compartment_name, config["tenancy"]
        ) +
        "Please try again with a correct parent compartment name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Parent Compartment Not Found\n")
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
        print("WARNING! - Child compartment {} not found in parent compartment {}\n\n".format(
            child_compartment_name, parent_compartment_name
            ) +
            "Please try again with a correct child compartment name"
             )
        raise RuntimeWarning("WARNING! - Child Compartment Not Found\n")

# now get the virtual network resources
virtual_networks = GetVirtualCloudNetworks(network_client, child_compartment.id, virtual_cloud_network_name)
virtual_networks.populate_virtual_cloud_networks()
virtual_network = virtual_networks.return_virtual_cloud_network()

# run through the logic and return the requested results
# 1st check to see if the target VCN already exists, create it if it is not present, otherwise exit with an exception
if virtual_network is None:
    print(
        "Virtual cloud network {} not found in child compartment {}\n".format(
            virtual_cloud_network_name,
            child_compartment_name
        ) +
        "Please try again with a correct name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Virtual cloud network not found")
elif option == "--force":
    result = delete_virtual_cloud_network(
        network_client,
        virtual_network.id
    )
    if result is None:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
    else:
        print("Virtual network {} deleted from child compartment {}\n".format(
            virtual_cloud_network_name,
            child_compartment_name
        ))
else:
    warning_beep(6)
    print("Enter YES to delete virtual cloud network {} from child compartment {}, or any other key to abort : ".format(
        virtual_cloud_network_name,
        child_compartment_name
    ))
    if "YES" == input():
        result = delete_virtual_cloud_network(
            network_client,
            virtual_network.id
        )
        if result is None:
            raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
        else:
            print("Virtual cloud network {} deleted from child compartment {}\n".format(
                virtual_cloud_network_name,
                child_compartment_name
            ))
    else:
        print("\nOci-DeleteVirtualNetwork aborted at user request\n")
