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
from time import sleep
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import return_availability_domain
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance

from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetVM.py : Usage\n\n" +
        "Oci-GetVM.py [parent compartment] [child compartment] [vm name] [region] [optional argument]\n\n" +
        "Use case example 1 gets information about all specified virtual machines within the specified compartment and region:\n" +
        "\tOci-GetVM.py admin_comp tst_comp list_all_vms_in_compartment 'us-ashburn-1'\n" +
        "Use case example 2 gets information about the specified VM instance within the specified compartment and region:\n" +
        "\tOci-GetVM.py admin_comp web_comp DKCDCP01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
region                          = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = [] # required for logic to work


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

# get VM instance data
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()


# run through the logic
if len(sys.argv) == 5 and sys.argv[3].upper() == "LIST_ALL_VMS_IN_COMPARTMENT":
    results = vm_instances.instance_list
    if len(results) == 0:
        print("N\n\nNo VM instances found within compartment {} in region {}\n\n".format(
            child_compartment_name,
            region
        ))
        raise RuntimeError("No VM instances in compartment")
    else:
        print(vm_instances.instance_list)
    exit(0)

error_trap_resource_not_found(
    vm_instance,
    "VM instance " + virtual_machine_name + " not found within compartment " + child_compartment_name + " within region " + region
)


'''
OCI does not have a simple way to get IP addresses from a VM instance. The ERD is:
                    vnic_attachment
                          x
                          x
                        vnic_id
                xxxxxxxxxxxxxxxxxxxxx
                x                   x
                x                   x
            instance_id------->private-ip.id
                                    x
                                    x
                               public_ip.id

We must associate a VNIC with an instance id, then associate all private IPs associated with
the correct vnic_id (which is returned as a list), then finally parse down all of the pub ips
in an availability domain with a private IP. Pay attention to the way OCI returns objects. In
this case, private IPs are returned as a list of for each vnic, and pubips are individual
objects that point back to particular private IPs.
'''
# get the private IP addresses for the VM instance
vnic_attachments = compute_client.list_vnic_attachments(
    compartment_id = child_compartment.id
).data
vnics = []
private_ips = []
pub_ips = []
for vnic in vnic_attachments:
    if vnic.instance_id == vm_instance.id and vnic.lifecycle_state != 'TERMINATED' and \
        vnic.lifecycle_state != 'TERMINATING':
        vnics.append(vnic)
        nic_priv_ips = network_client.list_private_ips(
            vnic_id = vnic.vnic_id
        ).data
        private_ips.append(nic_priv_ips)


# get the public IP addresses for the VM instance if present
avaiability_domain_public_ips = network_client.list_public_ips(
    scope = "AVAILABILITY_DOMAIN",
    compartment_id = child_compartment.id,
    availability_domain = vm_instance.availability_domain
).data

for ip in private_ips:
    count = len(ip)
    cntr = 0
    while cntr < count:
        for pubip in avaiability_domain_public_ips:
            if ip[cntr].id == pubip.assigned_entity_id:
                pub_ips.append(pubip)
        cntr += 1


if len(sys.argv) == 5:
    print(vm_instance)
    for ips in private_ips:
        print("Private IP Address:\t{}\n".format(ips))
    for pubip in pub_ips:
        print(pubip)
elif option == "--OCID":
    print(vm_instance.id)
elif option == "--NAME":
    print(vm_instance.display_name)
elif option == "--AVAILABILITY-DOMAIN":
    print(vm_instance.availability_domain)
elif option == "--LIFECYCLE-STATE":
    print(vm_instance.lifecycle_state)
elif option == "--METADATA":
    print(vm_instance.metadata)
elif option == "--NO-IP":
    print(vm_instance)
elif option == "--PUB-IP":
    for pubip in pub_ips:
        print("Public IP Address:\t" + pubip.ip_address)
elif option == "--PRIV-IP":
    for ip in private_ips:
        count = len(ip)
        cntr = 0
        while cntr < count:
            print("Private IP Address:\t" + ip[cntr].ip_address)
            cntr += 1
elif option == "--SHAPE":
    print(vm_instance.shape)
    print(vm_instance.shape_config)
elif option == "--SOURCE-DETAILS":
    print(vm_instance.source_details)
    image_details = compute_client.get_image(
        image_id = vm_instance.source_details.image_id
    ).data
    if image_details is not None:
        #print(image_details)
        print(
            "Original source name:\t\t" + image_details.display_name +
            "\nOriginal source OS type:\t" + image_details.operating_system +
            "\nOriginal source OS version:\t" + image_details.operating_system_version +
            "\nOriginal Source Created On:\t" + str(image_details.time_created)
        )
    else:
        print("Original source details no longer present in tenancy")
else:
    print(
        "\n\nINVALID OPTIONS! - Valid options are:\n\n" +
        "\t--ocid\t\t\tPrint the OCID of the VM resource\n" +
        "\t--name\t\t\tPrint the name of the VM resource\n" +
        "\t--availability-domain\tPrint the availability domain where the VM resource resides\n" +
        "\t--lifecycle-state\tPrint the lifecycle state of the VM resource\n" +
        "\t--metadata\t\tPrint the metadata of the VM resource\n" +
        "\t--no-ip\t\t\tPrint information about the VM instance resource without IP address information\n" +
        "\t--pub-ip\t\tPrint all public IP addresses associated with the VM resource\n" +
        "\t--priv-ip\t\tPrint all private IP addresses associated with the VM resource\n" +
        "\t--shape\t\t\tPrint the shape details of the VM resource\n" +
        "\t--source-details\tPrint the source details from which this VM resource had been created from\n\n" +
        "Please try again with a correct option.\n\n"
    )