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
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.subnets import add_subnet
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import CreateSubnetDetails

if len(sys.argv) != 10: # ARGS PLUS COMMAND
    print(
        "\n\nOci-AddVirtualCloudSubNetwork.py : Correct Usage\n\n" +
        "Oci-AddVirtualCloudSubNetwork.py [parent compartment name] [child compartment name] [vcn name]" +
        "[subnet name] [subnet dns name] [prohibit public IP address (True/False)]" +
        "[route table name] [security list name] [region]\n\n" +
        "Use case example 1 adds virtual cloud subnetwork within the specified virtual cloud network\n\n" +
        "\tOci-AddVirtualCloudSubNetwork.py admin_comp auto_comp auto_vcn auto_sub01 autosub01 \\ \n" +
        "\tfalse auto_rtb 'Default Security List for auto_vcn' 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning(
        "EXCEPTION! Incorrect Usage"
    )

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
subnet_name                     = sys.argv[4]
subnet_dns_name                 = sys.argv[5]
prohibit_pub_ip_addresses       = sys.argv[6]
route_table_name                = sys.argv[7]
security_list_name              = sys.argv[8]
region                          = sys.argv[9]

# set boolean value for prohibit_pub_ip_addresses based on string input, or abort if invalid entry
if prohibit_pub_ip_addresses.upper() == "TRUE":
    prohibit_pub_ip_addresses = True
elif prohibit_pub_ip_addresses.upper() == "FALSE":
    prohibit_pub_ip_addresses = False
else:
    print(
        "\n\nEXCEPTION! - Valid input for prohibit_pub_ip_addresses must either be 'true' or 'false'.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage\n")