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
from lib.gateways import delete_nat_gateway
from lib.gateways import GetNatGateway
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import CreateNatGatewayDetails


copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-DeleteNatGateway.py : Correct Usage\n\n" +
        "Oci-DeleteNatGateway.py [parent compartment] [child compartment] [virtual cloud network] " +
        "[NAT gateway name] [region]\n\n" +
        "Use case example deletes the NAT gateway to the specified virtual cloud network without prompting the user\n\n" +
        "\tOci-DeleteNatGateway.py admin_comp auto_comp auto_vcn auto_ngw 'us-ashburn-1' --force\n" +
        "\tRemove the --force option to be prompted prior to deleting the NAT gateway.\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect usage\n")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
virtual_cloud_network_name  = sys.argv[3]
nat_gateway_name            = sys.argv[4]
region                      = sys.argv[5]
if len(sys.argv) == 7:
    option = sys.argv[6]
else:
    option = [] # necessary for login to work

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

config["region"]    = region # Must set the cloud region
identity_client     = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client      = VirtualNetworkClient(config) # builds the network client method, required to manage network resources


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

# Get the NAT gateway resources
nat_gateways = GetNatGateway(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    nat_gateway_name
)
nat_gateways.populate_nat_gateways()
nat_gateway = nat_gateways.return_nat_gateway()


# run through the logic
if nat_gateway is not None:
    if option == "--force":
        results = delete_nat_gateway(
            network_client,
            nat_gateway.id
        )
        if results is not None:
            print("Nat gateway {} successfully deleted from virtual cloud network {}\n".format(
                nat_gateway_name,
                virtual_cloud_network_name
            ))
        else:
            raise RuntimeError("EXCEPTION! - UNKNOWN ERROR\n")
        
    elif len(option) == 0:
        warning_beep(6)
        print(
            "Enter YES to delete NAT gateway {} or any other key to abort".format(
                nat_gateway_name
            )
        )
        if "YES" == input():
            results = delete_nat_gateway(
            network_client,
            nat_gateway.id)

            if results is not None:
                print("Nat gateway {} successfully deleted from virtual cloud network {}\n".format(
                    nat_gateway_name,
                    virtual_cloud_network_name
                ))
            else:
                raise RuntimeError("EXCEPTION! - UNKNOWN ERROR\n")

        else:
            print("Removal of NAT gateway aborted at user request.\n\n")

    
    else:
        print("\n\nInvalid option. The only valid option is --force. Please try again.\n\n")
        raise RuntimeWarning("WARNING! - Invalid option\n")
else:
    print(
        "\n\nWARNING! - NAT gateway {} not present in virtual cloud network {}\n".format(
            nat_gateway_name,
            virtual_cloud_network_name
        ) +
        "Duplicate NAT gateways are not permitted by this utility.\n\n"
    )
    raise RuntimeWarning("WARNING! - NAT Gateway already present\n")