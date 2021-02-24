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
from tabulate import tabulate
from time import sleep

# required OCI modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.filesystems import GetExport
from lib.filesystems import GetFileSystem
from lib.filesystems import GetMountTarget
from lib.subnets import GetPrivateIP
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.file_storage import FileStorageClient
from oci.core import VirtualNetworkClient


if len(sys.argv) < 7 or len(sys.argv) > 8:
    print(
        "\n\nOci-GetMountTarget.py : Usage\n\n" +
        "Oci-GetMountTarget.py [parent compartment] [child compartment] [virtual cloud network]\n" +
        "[subnet] [mount target] [region]\n" +
        "Use case example 1 prints all mount targets within the specified compartment and lists them by name and state:\n" +
        "\tOci-GetMountTarget.py admin_comp dbs_comp dbs_vcn dbs_sub list_all_mount_targets 'us-ashburn-1' --short\n" +
        "Use case example 2 prints detailed information about the secified mount target:\n" +
        "\tOci-GetMountTarget.py admin_comp dbs_comp dbs_vcn dbs_sub KENTFST01_MT 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
virtual_cloud_network_name              = sys.argv[3]
subnet_name                             = sys.argv[4]
mount_target_name                       = sys.argv[5]
region                                  = sys.argv[6]
if len(sys.argv) == 8:
    option = sys.argv[7].upper()
else:
    option = None # required for logic to work
if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching tenant resource data, please wait......\n")


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

config["region"]                    = region # Must set the cloud region
identity_client                     = IdentityClient(config) # builds the identity client method, required to manage compartments
filesystem_client = FileStorageClient(config)
network_client = VirtualNetworkClient(config)


# get the parent compartment data
parent_compartments                 = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment                  = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Child compartment " + child_compartment_name + " within parent compartment " + parent_compartment_name
)

# All ADs must be searched by GetFileSystem, so get them
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# Now check to see if the mount target exists, if not raise exception
mount_targets = GetMountTarget(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
mount_targets.populate_mount_targets()
mount_target = mount_targets.return_mount_target(mount_target_name)

# run through the logic
# if len(sys.argv) == 8 and mount_target_name.upper() == "LIST_ALL_MOUNT_TARGETS":
#     header = ["COMPARTMENT", "MOUNT TARGET", "STATE"]
#     data_rows = []
#     for mt in mount_targets.return_all_mount_targets():
#         data_row = [
#             child_compartment_name,
#             mt.display_name,
#             mt.lifecycle_state
#         ]
#         data_rows.append(data_row)
#     print(tabulate(data_rows, headers = header, tablefmt = "grid_tables"))
#     print("\n\n")

# elif len(sys.argv) == 8 and mount_target_name.upper() == "LIST_ALL_MOUNT_TARGETS" and option == "--NAME":
#     header = ["NAME"]
#     data_rows = []
#     for mt in mount_targets.return_all_mount_targets():
#         data_row = [mt.display_name]
#         data_rows.append(data_row)
#     print(tabulate(data_rows, headers = header, tablefmt = "simple"))

if len(sys.argv) == 7 and mount_target_name.upper() == "LIST_ALL_MOUNT_TARGETS":
    # print(mount_targets.return_all_mount_targets())
    header = [
        "COMPARTMENT",
        "MOUNT TARGET",
        "STATE",
        "REGION"]
    data_rows = []
    for mt in mount_targets.return_all_mount_targets():
        data_row = [
            child_compartment_name,
            mt.display_name,
            mt.lifecycle_state,
            region
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))
    print("\n\n")

else:
    error_trap_resource_not_found(
        mount_target,
        "Mount target " + mount_target_name + " not found in compartment " + child_compartment_name + " within region " + region
    )
    # get the VCN, subnet, and private IP data

    virtual_cloud_networks = GetVirtualCloudNetworks(
        network_client,
        child_compartment.id,
        virtual_cloud_network_name
    )
    virtual_cloud_networks.populate_virtual_cloud_networks()
    virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
    error_trap_resource_not_found(
        virtual_cloud_network,
        "Virtual cloud network " + virtual_cloud_network_name + " not found in compartment " + child_compartment_name
    )

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
        "Subnet " + subnet_name + " not found within virtual cloud network " + virtual_cloud_network_name
    )

    priv_ip_addresses = GetPrivateIP(
        network_client,
        subnet.id
    )
    priv_ip_addresses.populate_ip_addresses()
    ip_address = priv_ip_addresses.return_ip_by_ocid(mount_target.private_ip_ids[0]) # current code release onlyt gets 1st ip

    # ok, that was a ton of code to get 1 chunk of data, thanks OCI for all the love!
    # Now we can do the easy stuff

    if len(sys.argv) == 7:
        # print(mount_target)
        # print(ip_address)
        header = [
            "COMPARTMENT",
            "MOUNT TARGET",
            "AVAILABILITY DOMAIN",
            "SERVICE IP ADDRESS",
            "LIFECYCLE STATUS",
            "REGION"
        ]
        data_rows = [[
            child_compartment_name,
            mount_target.display_name,
            mount_target.availability_domain,
            ip_address.ip_address,
            mount_target.lifecycle_state,
            region
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\n\nMOUNT TARGET ID :\t" + mount_target.id + "\n\n")
    elif option == "--OCID":
        print(mount_target.id)
    elif option == "--NAME":
        print(mount_target.display_name)
    elif option == "--LIFECYCLE-STATE":
        print(mount_target.lifecycle_state)
    elif option == "--JSON":
        print(mount_target)
        print(ip_address)
    else:
        print(
            "\n\nINVALID OPTION! - Valid options are:\n" +
            "\t--ocid\t\t\tPrints the OCID of the mount point\n" +
            "\t--name\t\t\tPrints the name of the mount target\n" +
            "\t--lifecycle-state\tPrints the state of the mount target\n" +
            "\t--json\t\t\tPrints all resource data in JSON format and surpresses other output\n" +
            "Please try again with the correct option.\n\n"
        )
        raise RuntimeWarning("INVALID OPTION!")


    


    




