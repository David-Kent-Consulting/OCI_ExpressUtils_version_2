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
from datetime import datetime
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
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.compute import GetVnicAttachment
from lib.securitygroups import GetNetworkSecurityGroup
from lib.subnets import GetPrivateIP
from lib.subnets import GetPublicIpAddress
from lib.subnets import GetSubnet
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeBackups

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient


# functions

def print_options():
    print(
        "\n\nValid options are:\n\n" +
        "\t--ocid\t\t\tPrint the OCID of the VM resource\n" +
        "\t--name\t\t\tPrint the name of the VM resource\n" +
        "\t--availability-domain\tPrint the availability domain where the VM resource resides\n" +
        "\t--lifecycle-state\tPrint the lifecycle state of the VM resource\n" +
        "\t--metadata\t\tPrint the metadata of the VM resource\n" +
        "\t--pub-ip\t\tPrint all public IP addresses associated with the VM resource\n" +
        "\t--priv-ip\t\tPrint all private IP addresses associated with the VM resource\n" +
        "\t--shape\t\t\tPrint the shape details of the VM resource\n" +
        "\t--source-details\tPrint the source details from which this VM resource had been created from\n" +
        "\t--json\t\t\tPrint all resource data in JSON format and surpresses other output\n\n"
    )
# end function print_options()

# see if the user is requesting options help
if len(sys.argv) == 2 and sys.argv[1].upper() == "--OPTIONS":
    print_options()
    exit(0)

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetVm.py : Usage\n\n" +
        "Oci-GetVm.py [parent compartment] [child compartment] [VM] [region] [optional argument]\n" +
        "Use case example 1 gets information about all specified virtual machines within the specified compartment and region:\n" +
        "\tOci-GetVm.py admin_comp tst_comp list_all_vms 'us-ashburn-1'\n" +
        "Use case example 2 gets information about the specified VM instance within the specified compartment and region:\n" +
        "\tOci-GetVm.py admin_comp web_comp DKCDCP01 'us-ashburn-1'\n\n" +
        "This utility will only list the private and public IP addresses that are associated with the\n" +
        "VM instance's primary virtual network interface. Please use the OCI console for managing multiple\n" +
        "vnics when your situation warrants it.\n\n" +
        "Run Oci-GetVm.py --options to get a list of optional arguments for this utility.\n\n" +
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
if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching and validating tenancy resource data......\n")

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
storage_client = BlockstorageClient(config) # builds the storage client method, required to get volume resources
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


# get VM instance data
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()

'''
OCI does not have a simple way to get IP addresses from a VM instance. The ERD is:

                    vnic_attachment
                          x
                          x
                        vnic_id
                xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                x                   x                       x
                x                   x                       x
            instance_id------->private-ip.id            subnet_id
                                    x                       x
                                    x                       x
                               public_ip.id              vcn_id

We must associate a VNIC with an instance id, then associate all private IPs associated with
the correct vnic_id (which is returned as a list), then finally parse down all of the pub ips
in an availability domain with a private IP. Pay attention to the way OCI returns objects. In
this case, private IPs are returned as a list of for each vnic, and pubips are individual
objects that point back to particular private IPs.
'''

# get the vnics and private IP addresses for the VM instance
vnic_attachments = GetVnicAttachment(
    compute_client,
    child_compartment.id
)
vnic_attachments.populate_vnics()

# get the public IP address. There can only be one empheral public IP address
# per instance. It is always bound to the NIC at index 0
compartment_public_ip_addresses = GetPublicIpAddress(
    network_client,
    availability_domains,
    child_compartment.id
)
compartment_public_ip_addresses.populate_public_ip_addresses()

# here's our header we use for tabulate on VMs
header = [
    "COMPARTMENT",
    "VM NAME",
    "AVAILABILITY\nDOMAIN",
    "VCN",
    "SUBNET",
    "primary\nIP ADDRESS",
    "PUBLIC\nIP ADDRESS",
    "SHAPE",
    "LIFECYCLE\nSTATE",
    "REGION"
]


# run through the logic
if len(sys.argv) == 5 and sys.argv[3].upper() == "LIST_ALL_VMS":
    data_rows = []
    if vm_instances.return_all_instances() is not None:
        for vm in vm_instances.return_all_instances():
            for vnic in vnic_attachments.return_all_vnics():
                if vnic.instance_id == vm.id:
                    subnet = network_client.get_subnet(subnet_id = vnic.subnet_id).data
                    virtual_cloud_network = network_client.get_vcn(vcn_id = subnet.vcn_id).data
                    subnet_ip_addresses = GetPrivateIP(
                        network_client,
                        subnet.id
                    )
                    subnet_ip_addresses.populate_ip_addresses()
                    vm_ip_addresses = []
                    for ip in subnet_ip_addresses.return_all_ip_addresses():
                        if ip.vnic_id == vnic.vnic_id:
                            vm_ip_addresses.append(ip)

                    vm_pub_ip = compartment_public_ip_addresses.return_public_ip_from_priv_ip_id(vm_ip_addresses[0].id)
                    if vm_pub_ip is None:
                        pub_ip = ""
                    else:
                        pub_ip = vm_pub_ip.ip_address

            data_row = [
                child_compartment.name,
                vm.display_name,
                vm.availability_domain,
                virtual_cloud_network.display_name,
                subnet.display_name,
                vm_ip_addresses[0].ip_address,
                pub_ip,
                vm.shape,
                vm.lifecycle_state,
                region
            ]
            data_rows.append(data_row)

    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    
    error_trap_resource_not_found(
        vm_instance,
        "Virtual Machine " + virtual_machine_name + " not found within compartment " + child_compartment_name + " in region " + region 
    )
    
    # just get the vnic, subnet, vnc, priv ip, and pub ip resource data for this VM instance

    vm_vnics = []
    for vnic in vnic_attachments.return_all_vnics():

        if vnic.instance_id == vm_instance.id:
            vm_vnics.append(vnic)
            subnet = network_client.get_subnet(subnet_id = vnic.subnet_id).data
            virtual_cloud_network = network_client.get_vcn(vcn_id = subnet.vcn_id).data
            subnet_ip_addresses = GetPrivateIP(
                network_client,
                subnet.id
            )
            subnet_ip_addresses.populate_ip_addresses()
            vm_ip_addresses = []
            for ip in subnet_ip_addresses.return_all_ip_addresses():
                if ip.vnic_id == vnic.vnic_id:
                    vm_ip_addresses.append(ip)
    
    vm_pub_ip = compartment_public_ip_addresses.return_public_ip_from_priv_ip_id(vm_ip_addresses[0].id)
    if vm_pub_ip is None:
        pub_ip = ""
    else:
        pub_ip = vm_pub_ip.ip_address

    # ok, we have all the data, let's go through the logic
    if len(sys.argv) == 5:  # no options, just print a summary table with select VM resource data
        data_rows = [[
            child_compartment.name,
            vm_instance.display_name,
            vm_instance.availability_domain,
            virtual_cloud_network.display_name,
            subnet.display_name,
            vm_ip_addresses[0].ip_address,
            pub_ip,
            vm_instance.shape,
            vm_instance.lifecycle_state
        ]]

        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\nVM OCID :\t" + vm_instance.id + "\n\n")

    # run through the remaining options
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

    elif option == "--PUB-IP":

        if len(pub_ip) == 0:
            print("\n\nNo public IP address assigned to VM instance {}.\n\n".format(
                virtual_machine_name))
        else:
            print(pub_ip)

    elif option == "--PRIV-IP":

        header = [
            "COMPARTMENT",
            "VM",
            "IP ADDRESS",
            "VNIC ID"
        ]
        data_rows = []
        for vnic in vm_vnics:
            ip_addresses = []
            vnic_ip_addresses = subnet_ip_addresses.return_ip_by_vnic_id(vnic.vnic_id)
            for ip in vnic_ip_addresses:
                ip_addresses.append(ip.ip_address)
            data_row = [
                child_compartment.name,
                vm_instance.display_name,
                ip_addresses,
                vnic.id
            ]
            data_rows.append(data_row)
        
        print(
            "\n\nOnly VNICs in the same compartment as the VM are shown. Use the OCI console to view\n" +
            "VNICs and their IP addresses if located in different compartments.\n"
        )
        print(tabulate(data_rows, headers = header, tablefmt = "grid"))
    
    elif option == "--SHAPE":
        # we omit max_vnic_attachments since it is buggy
        header = [
            "SHAPE",
            "OCPUS",
            "MEMORY IN GB",
            "BANDWIDTH IN Gbit/s",
            "CPU DESCRIPTION"
        ]
        data_rows = [[
            vm_instance.shape,
            vm_instance.shape_config.ocpus,
            vm_instance.shape_config.memory_in_gbs,
            vm_instance.shape_config.networking_bandwidth_in_gbps,
            vm_instance.shape_config.processor_description
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))

    elif option == "--SOURCE-DETAILS":

        image_details = compute_client.get_image(
            image_id = vm_instance.source_details.image_id
        ).data

        if image_details is not None:
            
            print(tabulate(
                [[
                    image_details.display_name,
                    image_details.operating_system,
                    image_details.operating_system_version,
                    image_details.time_created.ctime()
                ]],
                headers = [
                    "IMAGE NAME",
                    "IMAGE OS",
                    "IMAGE OS VERSION",
                    "CREATION DATE"
                ],
                tablefmt = "simple"
            ))
        
        else:
            print("Original source details no longer present in tenancy")
    
    elif option == "--JSON":
        print(vm_instance)
    else:
        print_options()
        print("Please try again with a correct option.\n\n")
        raise RuntimeWarning("INVALID OPTION!")

exit(0)
