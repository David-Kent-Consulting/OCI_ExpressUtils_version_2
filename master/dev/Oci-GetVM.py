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
from lib.general import get_regions
from lib.general import return_availability_domain
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import GetInstance
from lib.compute import GetVnicAttachment
from lib.subnets import GetPrivateIP
from lib.subnets import GetPublicIpAddress
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient

copywrite()
sleep(2)
if len(sys.argv) < 7 or len(sys.argv) > 8:
    print(
        "\n\nOci-GetVM.py : Usage\n\n" +
        "Oci-GetVM.py [parent compartment] [child compartment] [virtual cloud network]\n" +
        "[subnet] [vm instance] [region] [optional argument]\n\n" +
        "Use case example 1 gets information about all specified virtual machines within the specified compartment and region:\n" +
        "\tOci-GetVM.py admin_comp tst_comp tst_vcn tst_sub list_all_vms 'us-ashburn-1'\n" +
        "Use case example 2 gets information about the specified VM instance within the specified compartment and region:\n" +
        "\tOci-GetVM.py admin_comp web_comp web_vcn web_sub DKCDCP01 'us-ashburn-1'\n\n" +
        "This utility will only list the private and public IP addresses that are associated with the\n" +
        "VM instance's primary virtual network interface. Please use the OCI console for managing multiple\n" +
        "vnics when your situation warrants it.\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
subnet_name                     = sys.argv[4]
virtual_machine_name            = sys.argv[5]
region                          = sys.argv[6]
if len(sys.argv) == 8:
    option = sys.argv[7].upper()
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

# get availability domains
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# get vcn data
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name
)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
error_trap_resource_not_found(
    virtual_cloud_network,
    "Virtual cloud network " + virtual_cloud_network_name + " not found within compartment " + child_compartment_name + " in region " + region
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
    "Subnetwork " + subnet_name + " not found within virtual cloud network " + virtual_cloud_network_name + " in region " + region
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
if len(sys.argv) == 7 and sys.argv[5].upper() == "LIST_ALL_VMS":
    results = vm_instances.instance_list
    if len(results) == 0:
        print("\n\nNo VM instances found within compartment {} in region {}\n\n".format(
            child_compartment_name,
            region
        ))
        raise RuntimeError("No VM instances in compartment")
    else:
        header = [
            "VM NAME",
            "AVAILABILITY DOMAIN",
            "SHAPE",
            "LIFECYCLE STATE"
        ]
        data_rows = []
        for vm in vm_instances.instance_list:
            data_row = [
                vm.display_name,
                vm.availability_domain,
                vm.shape,
                vm.lifecycle_state
            ]
            data_rows.append(data_row)
        print(tabulate(data_rows, headers = header, tablefmt = "grid"))
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
# get the vnics and private IP addresses for the VM instance
compartment_vnic_attachments = GetVnicAttachment(
    compute_client,
    child_compartment.id
)
compartment_vnic_attachments.populate_vnics()
vnic_attachments = compartment_vnic_attachments.return_vnic(vm_instance.id)

# for vnic_attachment in vnic_attachments:
#     print(vnic_attachment)

compartment_private_ip_addresses = GetPrivateIP(
    network_client,
    subnet.id
)
compartment_private_ip_addresses.populate_ip_addresses()
private_ip_addresses = []
for ip in compartment_private_ip_addresses.return_all_ip_addresses():
    for vnic_attachment in vnic_attachments:
        if ip.vnic_id == vnic_attachment.vnic_id:
            private_ip_addresses.append(ip)


# get the public IP address. There can only be one empheral public IP address
# per instance. It is always bound to the NIC at index 0
compartment_public_ip_addresses = GetPublicIpAddress(
    network_client,
    availability_domains,
    child_compartment.id
)
compartment_public_ip_addresses.populate_public_ip_addresses()
public_ip_address = compartment_public_ip_addresses.return_public_ip_from_priv_ip_id(private_ip_addresses[0].id)
# print(public_ip_address)


# now we can run through the logic
if len(sys.argv) == 7:
    print(vm_instance)
    for ip_address in private_ip_addresses:
        print("Private IP Address:\t{}".format(ip_address.ip_address))
    print("Public IP Address:\t{}\n".format(public_ip_address.ip_address))
    print(
        "Private IP addresses are only shown for the primary virtual network interface.\n" +
        "Please use the OCI console to manage private IP addresses on VM instances with\n" +
        "multiple virtual network interfaces.\n\n"
    )
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
elif option == "--NSG":
    data_rows = []
    for vnic in vnic_attachments:
        get_vnic_response = network_client.get_vnic(
            vnic_id = vnic.vnic_id
        ).data

        if len(get_vnic_response.nsg_ids) > 0:
            #print(get_vnic_response.nsg_ids[0])
            get_nsg_response = network_client.get_network_security_group(
                network_security_group_id = get_vnic_response.nsg_ids[0]
            ).data
            data_row = [
                vnic.vnic_id,
                get_nsg_response.display_name
            ]
        else:
            data_row = [vnic.vnic_id, None]
        data_rows.append(data_row)
    header = ["VNIC ID", "NETWORK SECURITY GROUP ASSIGNMENT"]
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

elif option == "--PUB-IP":
    print(public_ip_address.ip_address)
elif option == "--PRIV-IP":
    for ip_address in private_ip_addresses:
        print("Private IP Address:\t{}".format(ip_address.ip_address))
    print(
        "\nPrivate IP addresses are only shown for the primary virtual network interface.\n" +
        "Please use the OCI console to manage private IP addresses on VM instances with\n" +
        "multiple virtual network interfaces.\n\n"
    )
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