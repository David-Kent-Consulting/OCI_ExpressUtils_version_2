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
from tabulate import tabulate

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import is_int
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.filesystems import create_mount_target
from lib.filesystems import GetMountTarget
from lib.subnets import GetPrivateIP
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.file_storage import FileStorageClient
from oci.file_storage import FileStorageClientCompositeOperations

# required OCI decorators
from oci.file_storage.models import CreateMountTargetDetails

copywrite()
sleep(2)
if len(sys.argv) != 10:
    print(
        "\n\nOci-AddMountTarget.py : Usage\n\n" +
        "Oci-AddMountTarget.py [parent compartment] [child compartment] [availability domain number]\n" +
        "[virtual cloud network] [subnet] [mount target name name] [hostname] [ip address] [region]\n\n" +
        "Use case example creates the specified mount target within the specified compartment:\n" +
        "\tOci-AddMountTarget.py admin_comp dbs_comp 2 KENTFST01_MT KENTFST01 '172.16.0.125' 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]

if not is_int(sys.argv[3]):
    raise RuntimeWarning("INVALID VALUE! - Availability domain must be a number between 1 and 3")
availability_domain_number          = int(sys.argv [3])
if availability_domain_number not in [1,2,3]:
    raise RuntimeWarning("INVALID VALUE! - Availability domain must be a number between 1 and 3")

virtual_cloud_network_name          = sys.argv[4]
subnet_name                         = sys.argv[5]
mount_target_name                   = sys.argv[6]
mount_target_host_name              = sys.argv[7]
ip_address                          = sys.argv[8]
region                              = sys.argv[9]

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
filesystem_composite_client = FileStorageClientCompositeOperations(filesystem_client)
network_client = VirtualNetworkClient(config)

print("\n\nFetching tenant resource data, please wait......\n")
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

# get the AD name
availability_domain = return_availability_domain(
    identity_client,
    child_compartment.id,
    availability_domain_number
)

# All ADs must be searched by GetFileSystem, so get them
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# Now check to see of the mount target exists, if so raise exception
mount_targets = GetMountTarget(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
mount_targets.populate_mount_targets()
mount_target = mount_targets.return_mount_target(mount_target_name)
error_trap_resource_found(
    mount_target,
    "Mount target " + mount_target_name + " already present in compartment " + child_compartment_name + " within region " + region
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

# make sure the selected IP address is not already taken
priv_ip_addresses = GetPrivateIP(
    network_client,
    subnet.id
)
priv_ip_addresses.populate_ip_addresses()
if priv_ip_addresses.is_dup_ip(ip_address):
    warning_beep(1)
    print("\nPrivate IP address {} already assigned by subnet {} to another resource.\n".format(
        ip_address,
        subnet_name
    ))
    print("You must use a unique IP private IP address.\n\n")
    raise RuntimeWarning("DUPLICATE PRIVATE IP ADDRESS")

# create the mount target and return the results
print("Creating mount target {} within compartment {} , please wait.......\n".format(
    mount_target_name,
    child_compartment_name
))
create_mount_target_response = create_mount_target(
    filesystem_composite_client,
    CreateMountTargetDetails,
    availability_domain,
    child_compartment.id,
    mount_target_name,
    mount_target_host_name,
    subnet.id,
    ip_address
)

if create_mount_target_response is None:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
else:
    print("Mount target creation is complete. Please inspect the results below:\n\n")
    row_data = [
        child_compartment_name,
        create_mount_target_response.display_name,
        create_mount_target_response.id,
        availability_domain,
        create_mount_target_response.lifecycle_state
    ]
    print(tabulate([row_data], headers = ["COMPARTMENT NAME", "MOUNT TARGET NAME", "MOUNT TARGET ID", "AVAILABILITY DOMAIN", "STATUS"], tablefmt = "simple"))

