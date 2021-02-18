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

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import GetInputOptions
from lib.general import get_regions
from lib.general import is_int
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.compute import GetVnicAttachment
from lib.securitygroups import delete_vnic_from_network_security_group
from lib.securitygroups import GetNetworkSecurityGroup
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import UpdateVnicDetails

copywrite()
sleep(2)
if len(sys.argv) != 5:
    print(
        "\n\nOci-DeleteVmFromNetworkSecurityGroup.py : Usage\n\n" +
        "Oci-DeleteVmFromNetworkSecurityGroup.py [parent compartment] [child compartment]\n" +
        "[virtual machine] [region]\n\n" +
        "The following deletes the VM's primary virtual network interface from the VM's primary VNIC\n" +
        "\tOci-DeleteVmFromNetworkSecurityGroup.py admin_comp tst_comp kentesmt01 'us-ashburn-1'\n\n" +
        "This utility only supports de-assigning security groups to the VM instance's primary VNIC\n" +
        "Use cases with NSGs assgined to multiple VNICs on the same VM are not considered a best practice\n" +
        "and are not supported by this utility.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
virtual_machine_name                    = sys.argv[3]
region                                  = sys.argv[4]

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
compute_client = ComputeClient(config) # builds the compute client method, required to manage compute resources
network_client = VirtualNetworkClient(config) # builds the network client, required to manage network resources

print("\n\nFetching and validating tenancy resource data, please wait......\n")
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

# get the availability domains
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# get VM instance data
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()
error_trap_resource_not_found(
    vm_instance,
    "Virtual machine " + virtual_machine_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# get the VM's primary vnics
compartment_vnic_attachments = GetVnicAttachment(
    compute_client,
    child_compartment.id
)
compartment_vnic_attachments.populate_vnics()
vnic_attachments = compartment_vnic_attachments.return_vnic(vm_instance.id)

for nic in vnic_attachments:
    get_vnic_response = network_client.get_vnic(
        vnic_id = nic.vnic_id
    ).data
    if get_vnic_response.is_primary is True:
        break

print("Deleting virtual machine instance {} from all network security groups......".format(
    virtual_machine_name
))
update_vnic_response = delete_vnic_from_network_security_group(
    network_client,
    UpdateVnicDetails,
    get_vnic_response.id
)

print("Update successful, please inspect the results below.")
sleep(2)
header = [
    "VIRTUAL MACHINE",
    "VNIC NAME",
    "SECURITY GROUP ASSIGNMENT",
    "VNIC ID"
]
data_rows = [[
    virtual_machine_name,
    update_vnic_response.display_name,
    None,
    get_vnic_response.id
]]
print(tabulate(data_rows, headers = header, tablefmt = "grid"))
