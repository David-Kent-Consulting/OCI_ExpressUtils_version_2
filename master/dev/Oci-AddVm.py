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

#######################################################
### WARNING! WARNING! WARNING! WARNING! WARNING!    ###
###                                                 ###
### The python interpreter that matches the version ###
### installed with anaconda and pandas must be      ###
### loaded. Failure to do so will result in import  ###
### and runtime erroors.                            ###
###                                                 ###
### WARNING! WARNING! WARNING! WARNING! WARNING!    ###
#######################################################

'''
The system env var PATHONPATH must be exported in the shell's profile. It must point to the location of the OCI
libraries. This is typically in the same directory structure that the OCI CLI installs to, such as
~./lib/oracle-cli/lib/python3.8/site-packages 

Below find a literal example:

export PYTHONPATH=/Users/henrywojteczko/lib/oracle-cli/lib/python3.8/site-packages

See https://docs.python.org/3/tutorial/modules.html#the-module-search-path and
https://stackoverflow.com/questions/54598292/python-modulenotfounderror-when-trying-to-import-module-from-imported-package

Package requirements: Python 3.8.5 or later, conda, pandas.
Be certain your libpaths are correct for python otherwise pandas will not import.

'''

# required system modules
from detect_delimiter import detect
import pandas as pd
import os.path
import sys
from datetime import datetime
from time import sleep

# required DKC modules
from lib.general import get_availability_domains
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetCapacityReservations
from lib.compute import check_for_vm
from lib.compute import GetImages
from lib.compute import GetInstance
from lib.compute import launch_instance
from lib.compute import GetShapes
from lib.vcns import GetVirtualCloudNetworks
from lib.subnets import GetPrivateIP
from lib.subnets import GetSubnet

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import VirtualNetworkClient
from oci.core.models import CreateVnicDetails
from oci.core.models import InstanceSourceDetails
from oci.core.models import InstanceSourceViaImageDetails
from oci.core.models import LaunchInstanceDetails
from oci.core.models import LaunchInstanceShapeConfigDetails
from oci.core.models import LaunchOptions

copywrite()
sleep(2)
if len(sys.argv) < 14 or len(sys.argv) > 16:
    print(
        "\n\nOci-AddVm.py : Usage\n\n" +
        "Oci-AddVm.py [parent compartment] [child compartment] [virtual machine name] [boot vol in gb] [vcn name]\n" +
        "\t[subnet name] [source image name] [shape] [number of OCPUs] [Memory in GB] [private IP address]\n" +
        "\t[availability domain number] [region] [OPTION --ssh-key-file 'full path to ssh key file']\n\n" +
        "Use case example adds a Linux VM from an OCI marketplace image with the specified SSH key file.\n" +
        "Remove the option for --ssh-key-file if a key file is not required for the image, or if the\n" +
        "image is of type Windows.\n\n" +
        "\tOci-AddVm.py admin_comp tst_comp KENTWEB01 64 tst_vcn tst_sub 'Oracle-Linux-7.9-2021.12.08-0'\ \n" +
        "\t'VM.Standard.E4.Flex' 1 16 '172.16.4.4 2' 'us-ashburn-1' '/home/ansible/.ssh/id_rsa.pub'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )
    raise RuntimeWarning("INVALID USAGE\n")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_machine_name                = sys.argv[3].upper()
boot_volume_size_in_gbs             = int(sys.argv[4])
virtual_network_name                = sys.argv[5]
subnetwork_name                     = sys.argv[6]
image_name                          = sys.argv[7]
shape                               = sys.argv[8]
number_of_ocpus                     = float(sys.argv[9])
memory_in_gbs                       = float(sys.argv[10])
private_ip_address                  = sys.argv[11]
availability_domain_number          = int(sys.argv[12])
region                              = sys.argv[13]

if len(sys.argv) > 14:
    if sys.argv[14].upper() != "--SSH-KEY-FILE":
        print("{} is an invalid options. Please try again.\n".format(sys.argv[14]))
        raise RuntimeWarning("INVALID OPTION\n")
    else:
        if len(sys.argv) != 16:
            raise RuntimeWarning("A FILE NAME MUST BE SPECIFIED WITH --SSH-KEY-OPTION")
        else:
            ssh_public_key = sys.argv[15]
            f = open(sys.argv[15], "r")
            ssh_public_key = f.read()
else:
    ssh_public_key = None

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
compute_client = ComputeClient(config) # builds the network client method, required to manage network resources
compute_composite_client = ComputeClientCompositeOperations(compute_client)
network_client = VirtualNetworkClient(config)

print("\n\nFetching tenancy data, please wait......\n")
# get the parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment
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

# check to see if the VM is already present
virtual_machines = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
virtual_machines.populate_instances()
virtual_machine = virtual_machines.return_instance()

error_trap_resource_found(
    virtual_machine,
    "Virtual machine " + virtual_machine_name + " found within compartment " + child_compartment_name + " within region " + region
)

# Check to see if the requested image exists
images = GetImages(
    compute_client,
    child_compartment.id
)
images.populate_image_list()
image = images.return_image(image_name)

error_trap_resource_not_found(
    image,
    "Image " + image_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# get the network data
virtual_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_network_name
)
virtual_networks.populate_virtual_cloud_networks()
virtual_network = virtual_networks.return_virtual_cloud_network()

error_trap_resource_not_found(
    virtual_network,
    "Virtual network " + virtual_network_name + " not found in compartment " + child_compartment_name + " within region " + region
)

subnetworks = GetSubnet(
    network_client,
    child_compartment.id,
    virtual_network.id,
    subnetwork_name
)
subnetworks.populate_subnets()
subnetwork = subnetworks.return_subnet()

error_trap_resource_not_found(
    subnetwork,
    "Subnetwork " + subnetwork_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# Verify the selected IP address is not in use
private_ip_addresses = GetPrivateIP(
    network_client,
    subnetwork.id
)
private_ip_addresses.populate_ip_addresses()
private_ip_addr = private_ip_addresses.return_ip_by_address(private_ip_address)

error_trap_resource_found(
    private_ip_addr,
    "Private IP address " + private_ip_address + " already assigned to subnetwork " + subnetwork_name
)

# get the availability domain based on the supplied AD number.
# Logic must verify the range between 1-3 beforehand
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)
availability_domain = availability_domains[availability_domain_number - 1]

# valide the shape selection
my_shapes = GetShapes(compute_client, child_compartment.id)
my_shapes.populate_shapes()
my_shape = my_shapes.return_shape(shape)
if my_shape is None:
    raise RuntimeError("\nWARNING! Shape " + shape + " was not found. Please try again.\n\n")

print("Submitting request to launch instance {} in compartment {} within region {}, please wait......\n".format(
    virtual_machine_name,
    child_compartment_name,
    region
))

# old logic remove when completed wojteczko 16sep2024

launch_instance_response = launch_instance(
    compute_composite_client,
    CreateVnicDetails,
    InstanceSourceDetails,
    InstanceSourceViaImageDetails,
    LaunchInstanceDetails,
    LaunchInstanceShapeConfigDetails,
    LaunchOptions,
    boot_volume_size_in_gbs,
    child_compartment.id,
    subnetwork.id,
    availability_domain.name,
    private_ip_address,
    virtual_machine_name,
    shape,
    number_of_ocpus,
    memory_in_gbs,
    image.id,
    ssh_public_key
)

if launch_instance_response is not None and launch_instance_response.data.lifecycle_state not in ["TERMINATING", "TERMINATED", "UNKNOWN_ENUM_VALUE"]:
    print("Instance launch was successful. Please note the results below.\n\n")
    print(launch_instance_response.data)
else:
    print("Instance launch request ID {} failed. Please examine work request in the console and try again.\n".format(
        launch_instance_response.request_id
    ))
    raise RuntimeError("UNKNOWN ERROR\n")

