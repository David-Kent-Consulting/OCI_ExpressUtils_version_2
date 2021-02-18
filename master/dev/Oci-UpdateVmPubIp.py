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
from lib.compute import GetInstance
from lib.compute import get_vm_instance_response
from lib.compute import update_instance_name

# required OCI modules
from oci.config import from_file
from oci import wait_until
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import CreatePublicIpDetails


copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-UpdateVmPubIp.py : Usage\n\n" +
        "Oci-UpdateVmPubIp.py [parent compartment] [child compartment] [vm name] [region] [--enable/--disable] [--force]\n\n" +
        "Use case example 1 enables the VM instance public IP address for the specified virtual machine with no user prompt:\n" +
        "\tOci-UpdateVmPubIp.py admin_comp tst_comp KENTBAST01 'us-ashburn-1' --enable  --force\n\n" +
        "Omit the --force option if you wish to be prompted prior to updating the change.\n"
        "CAUTION! - The subnet the VM is assigned to must be enabled for public IP addresses in order to assign a public IP to\n" +
        "the instance's virtual network interface.\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect Usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
region                          = sys.argv[4]
action                          = sys.argv[5].upper()
if len(sys.argv) == 7:
    option = sys.argv[6].upper()
else:
    option = None # required for logic to work

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
# get the vnic data for the VM instance
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
for vnic in vnics:
    if vnic.nic_index == 0:
        primary_vnic = vnic
for private_ip in private_ips:
    for ip in private_ip:
        if ip.vnic_id == primary_vnic.vnic_id:
            primary_ip = ip

# get the public IP addresses for the VM instance if present
availability_domain_public_ips = network_client.list_public_ips(
    scope = "AVAILABILITY_DOMAIN",
    compartment_id = child_compartment.id,
    availability_domain = vm_instance.availability_domain
).data

pub_ip_present = False
for pub_ip in availability_domain_public_ips:
    if pub_ip.private_ip_id == primary_ip.id:
        pub_ip_present = True
        assigned_pub_ip = pub_ip

if action == "--ENABLE":

    if pub_ip_present:
        print("Public IP address already assigned to VM instance {}.\n".format(
            virtual_machine_name
        ))
        print("No action taken on VM instance.\n\n")
        exit(0)
    else:
        if len(sys.argv) == 6:
            warning_beep(6)
            print("Enter YES to enable a public IP address on VM instance {}, or any other key to abort".format(
                virtual_machine_name
            ))
            if "YES" != input():
                print("Action aborted per user request.\n\n")
                exit(0)
        elif option != "--FORCE":
            raise RuntimeWarning("INVALID OPTION! --force is the only valid option.")
        # we only create empheral IP addresses with this tool.
        results = network_client.create_public_ip(
            create_public_ip_details = CreatePublicIpDetails(
                compartment_id = child_compartment.id,
                display_name = virtual_machine_name + "_pubip",
                lifetime = "EPHEMERAL",
                private_ip_id = primary_ip.id
            )
        ).data

        if results is None:
            raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
        else:
            print("A public IP address is now assigned to VM instance {}. Please review the results below.\n".format(
                virtual_machine_name
            ))
            sleep(5)
            print(results)

elif action == "--DISABLE":
    if not pub_ip_present:
        print("There is no public IP address assigned to VM instance {}.\n".format(
            virtual_machine_name
        ))
        exit(0)
    else:
        if len(sys.argv) == 6:
            warning_beep(6)
            print("Enter YES to remove the public IP address from VM instance {}\n".format(
                virtual_machine_name
            ))
            if "YES" != input():
                print("Task aborted per user request.\n")
                exit(0)
        elif option != "--FORCE":
            raise RuntimeWarning("INVALID OPTION! --force is the only valid option.")
        
        results = network_client.delete_public_ip(
            public_ip_id = assigned_pub_ip.id
        )
        if results is None:
            raise RuntimeError("EXCEPTION! UNKNOWN ERROR.")
        else:
            print("The public IP address has been removed from VM instance {}..\n".format(
                virtual_machine_name
            ))


