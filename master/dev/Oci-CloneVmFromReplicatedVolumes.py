#!/usr/bin/python3

# Copyright 2019 – 2022
# David Kent Consulting, Inc.
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
from lib.general import get_subscriber_regions
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.backups import add_volume_to_backup_policy
from lib.backups import GetBackupPolicies
from lib.backups import delete_volume_backup_policy
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.compute import launch_instance_from_boot_volume
from lib.compute import stop_os_and_instance
from lib.vcns    import GetVirtualCloudNetworks
from lib.subnets import GetSubnet
from lib.subnets import GetPrivateIP
from lib.subnets import validate_ip_addr_is_in_subnet
from lib.volumes import attach_paravirtualized_volume
from lib.volumes import check_vm_replica_status
from lib.volumes import create_boot_volume_from_replica
from lib.volumes import create_volume_from_volume_replica
from lib.volumes import create_bootvol_replica
from lib.volumes import create_vol_replica
from lib.volumes import delete_bootvol_replica
from lib.volumes import delete_vol_replica
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeAttachment

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import BlockstorageClientCompositeOperations
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import VirtualNetworkClient

# required OCI modules for storage resource details
from oci.core.models import UpdateBootVolumeDetails
from oci.core.models import BootVolumeReplicaDetails
from oci.core.models import CreateBootVolumeDetails
from oci.core.models import BootVolumeSourceFromBootVolumeReplicaDetails
from oci.core.models import UpdateVolumeDetails
from oci.core.models import BlockVolumeReplicaDetails
from oci.core.models import CreateVolumeDetails
from oci.core.models import VolumeSourceFromBlockVolumeReplicaDetails
from oci.core.models import AttachParavirtualizedVolumeDetails

# required OCI modules for compute resource details
from oci.core.models import CreateVnicDetails
from oci.core.models import LaunchInstanceDetails
from oci.core.models import InstanceSourceDetails
from oci.core.models import CreateVnicDetails
from oci.core.models import LaunchOptions
from oci.core.models import LaunchInstanceShapeConfigDetails
from oci.core.models import InstanceSourceDetails
from oci.core.models import InstanceSourceViaBootVolumeDetails

copywrite()
if len(sys.argv) != 10:
    print(
        "\n\nOci-CloneVmFromReplicatedVolumes.py : Correct Usage\n\n" +
        "Oci-CloneVmFromReplicatedVolumes.py [parent compartment] [child compartment] [virtual machine name]\n" +
        "[source region] [target child compartment] [target virtual cloud network] [target subnetwork]\n" +
        "[target virtual machine private IP address] [target region]\n\n" +
        "Use case example clones the source virtual machine in the primary region to the child compartment\n" +
        "in the target region. Note this utility will not clone a VM to the parent compartment or to a\n" +
        "different parent/child compartment.\n\n" +
        "Oci-CloneVmFromReplicatedVolumes.py  admin_comp tst_comp kentjsubp01 'us-ashburn-1' \\\n" +
        "\tdbs_comp dr_vcn dbs_sub02 '172.16.129.4' 'us-phoenix-1\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! Incorrect usage\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_machine_name            = sys.argv[3]
region                          = sys.argv[4]
target_child_compartment_name   = sys.argv[5]
target_vcn_name                 = sys.argv[6]
target_subnet_name              = sys.argv[7]
target_vm_private_ip_address    = sys.argv[8]
dr_region                       = sys.argv[9]

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
    
correct_region = False
for rg in regions:
    if rg.name == dr_region:
        correct_region = True
        drconfig = from_file()
if not correct_region:
    print("\n\nWARNING! - DR Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        dr_region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

# instiate OCI methods
config["region"] = region # Must set the cloud region
drconfig["region"] = dr_region # Must set for the DR cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
dr_identity_client = IdentityClient(drconfig) # builds identity client for DR region
compute_client = ComputeClient(config) # builds the compute client method, required to manage compute resources
dr_compute_client = ComputeClient(drconfig) # builds the DR compute methods
dr_compute_client = ComputeClient(drconfig) # builds methods for compute client in DR region
dr_compute_composite_client = ComputeClientCompositeOperations(dr_compute_client) # required for compute composite ops
storage_client = BlockstorageClient(config) # builds the volume client method, required to manage block volume resources
dr_storage_client = BlockstorageClient(drconfig) # Builds storage methods
dr_storage_composite_client = BlockstorageClientCompositeOperations(dr_storage_client) # required for storage composite ops
dr_network_client = VirtualNetworkClient(drconfig) # Builds network methods

print("\nFetching cloud tenancy resource information......\n")

config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config)

# check primary and secondary region
regions = get_regions(identity_client)
correct_region = False
for rg in regions:
    if rg.name == region:
        correct_region = True
        
if not correct_region:
    print("\n\nWARNING! - Primary region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

correct_region = False
for rg in regions:
    if rg.name == dr_region:
        correct_region = True
        replica_region = rg
        
if not correct_region:
    print("\n\nWARNING! - Disaster recovery region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

# get parent and child compartments
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)
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

target_child_compartments = GetChildCompartments(
    parent_compartment.id,
    target_child_compartment_name,
    identity_client)
target_child_compartments.populate_compartments()
target_child_compartment = target_child_compartments.return_child_compartment()

# Make sure regions are accessible to tenancy
subscribed_regions = get_subscriber_regions(identity_client, parent_compartment.compartment_id)
region_state = False
dr_region_state = False
for rg in subscribed_regions:
    # rn = rg.region_name
    if rg.region_name == region:
        region_state = True
    if rg.region_name == dr_region:
        dr_region_state = True
        
if not region_state:
    raise RuntimeError("EXCEPTION! Primary region not in supplied value for region")
elif not dr_region_state:
    raise RuntimeWarning("WARNING! Disaster recovery region not subscribed to")

print("Fetching network and VM resource information......\n")

virtual_networks = GetVirtualCloudNetworks(dr_network_client, target_child_compartment.id, target_vcn_name)
virtual_networks.populate_virtual_cloud_networks()
virtual_network = virtual_networks.return_virtual_cloud_network()

error_trap_resource_not_found(
    virtual_network,
    "Virtual cloud network " + target_vcn_name + " not found in compartment " + target_child_compartment_name + " within region " + dr_region
)

virtual_cloud_subnetworks = GetSubnet(
    dr_network_client,
    target_child_compartment.id,
    virtual_network.id,
    target_subnet_name
)
virtual_cloud_subnetworks.populate_subnets()
virtual_cloud_subnetwork = virtual_cloud_subnetworks.return_subnet()

error_trap_resource_not_found(
    virtual_cloud_subnetwork,
    "Virtual cloud subnetwork " + target_subnet_name + " not found in compartment " + target_child_compartment_name + " within region " + dr_region
)

# make sure the target_ip_address is not allotted
private_ip_addresses = GetPrivateIP(
    dr_network_client,
    virtual_cloud_subnetwork.id
)
private_ip_addresses.populate_ip_addresses()

if private_ip_addresses.is_dup_ip(target_vm_private_ip_address):
    print("IP address {} already allotted to subnetwork {} in virtual cloud network {} in compartment {} within region {}\n".format(
    target_vm_private_ip_address,
    target_subnet_name,
    target_vcn_name,
    target_child_compartment_name,
    dr_region))
    print("Please try again with an unassigned private IP address.\n\n")
    raise RuntimeWarning("WARNING! Duplicate private IP address")

# make sure the private IP address is correctly formatted and that it is within the target subnet's CIDR range.
if not validate_ip_addr_is_in_subnet(virtual_cloud_subnetwork.cidr_block, target_vm_private_ip_address):
    print("IP address {} not in subnet {}.\nPlease try again with a correct IP address.\n\n".format(
        target_vm_private_ip_address,
        virtual_cloud_subnetwork.cidr_block))
    raise RuntimeWarning("WARNING! Invalid IP Address\n\n")

# Make sure the VM we want to create in the DR region does not exist
target_vm_instances = GetInstance(
    dr_compute_client,
    target_child_compartment.id,
    virtual_machine_name)
target_vm_instances.populate_instances()
dr_vm_instance = target_vm_instances.return_instance()

error_trap_resource_found(
    dr_vm_instance,
    "Virtual machine " + virtual_machine_name + " already exists in " + target_child_compartment_name + " within region " + dr_region
)

# make sure the VM we are looking for exists
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name,
    
    
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()

error_trap_resource_not_found(
    vm_instance,
    "Virtual machine instance " + virtual_machine_name + " not found within compartment " + child_compartment_name + " in region " + region
)

# Get the availability domains for the VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# get the boot and block voliume attachments
boot_vol_attachments = get_boot_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id
    )

block_vol_attachments = get_block_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id)

volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()

# get the boot and block voliume attachments
boot_vol_attachments = get_boot_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id
    )

block_vol_attachments = get_block_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id)

volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()

# get the boot and block volumes that are attached to the VM instance
boot_volumes = []
for boot_vol_attachment in boot_vol_attachments:
    boot_volume = volumes.return_boot_volume(boot_vol_attachment.boot_volume_id)
    boot_volumes.append(boot_volume)

block_volumes = []
for block_volume_attachment in block_vol_attachments:
    block_volume = volumes.return_block_volume(block_volume_attachment.volume_id)
    block_volumes.append(block_volume)

# validate the replicated state of the VM's disks
if not check_vm_replica_status(
    dr_storage_client,
    boot_volumes,
    block_volumes):
    
    print("Either a boot volume or block volume replica is in an invalid state for virtual machine {}\n".format(virtual_machine_name))
    print("Please inspect the boot volume and volumes with GetVmVolumeReplicas.py or another tool\n" +
          "and correct the issue, and then try this utility again.\n\n")
    raise RuntimeError("EXCEPTION! At least 1 boot or block volume replica is in an invalid state")

# This code prepares the fully qualified domain name where the disk volumes will be created
ad_number = boot_volume.availability_domain[-1]
# we need to set the target AD, we get this by calling return_availability_domain and passing the AD number from the primary volume
volume_target_availability_domain = return_availability_domain(dr_identity_client, target_child_compartment.id, int(boot_volume.availability_domain[-1]))

print("Creating the disks in target child compartment {} within region {}......\n".format(
    target_child_compartment_name,
    dr_region
))

# create the boot volume
for bv in boot_volumes:
    create_boot_volume_response = create_boot_volume_from_replica(
        dr_storage_composite_client,
        BootVolumeSourceFromBootVolumeReplicaDetails,
        CreateBootVolumeDetails,
        target_child_compartment.id,
        volume_target_availability_domain,
        bv.display_name,
        bv.size_in_gbs,
        bv.boot_volume_replicas[0].boot_volume_replica_id,
        bv.vpus_per_gb
    )
    
    if create_boot_volume_response is None:
        print("Unable to create boot volume {} in target child compartment {} within region {}\n".format(
            bv.display_name,
            target_child_compartment_name,
            dr_region
        ))
        raise RuntimeError("EXCEPTION! Unknown Error!")
    else:
        dr_boot_volume = create_boot_volume_response.data

# create the block volumes

bv_list = []
for bv in block_volumes:
    create_volume_from_volume_replica_response = create_volume_from_volume_replica(
        dr_storage_composite_client,
        CreateVolumeDetails,
        VolumeSourceFromBlockVolumeReplicaDetails,
        target_child_compartment.id,
        volume_target_availability_domain,
        bv.display_name,
        bv.size_in_gbs,
        bv.block_volume_replicas[0].block_volume_replica_id,
        bv.vpus_per_gb
    )

    if create_volume_from_volume_replica_response.data.lifecycle_state not in ["CREATING", "AVAILABLE", "PROVISIONING"]:
        print("Unable to create volume {} in target child compartment {} within region {}\n".format(
            bv.display_name,
            target_child_compartment_name,
            dr_region
        ))
        raise RuntimeError("EXCEPTION! Unknown Error!")
    else:
        bv_list.append(create_volume_from_volume_replica_response.data)

# create the VM instance from the cloned boot volume
print("Launching virtual machine instance clone {} in target child compartment {} within region {}......\n".format(
    virtual_machine_name,
    target_child_compartment_name,
    region
))

if vm_instance.shape not in ["VM.Standard.E3.Flex","VM.Standard.E4.Flex"]:
    shape_config = None
else:
    shape_config = LaunchInstanceShapeConfigDetails(
        ocpus = vm_instance.shape_config.ocpus,
        memory_in_gbs = vm_instance.shape_config.memory_in_gbs
    )

launch_instance_from_boot_volume_response = launch_instance_from_boot_volume(
    dr_compute_composite_client,
    LaunchInstanceDetails,
    CreateVnicDetails,
    LaunchOptions,
    InstanceSourceDetails,
    InstanceSourceViaBootVolumeDetails,
    volume_target_availability_domain,
    target_child_compartment.id,
    vm_instance.shape,
    vm_instance.display_name,
    target_vm_private_ip_address,
    virtual_cloud_subnetwork.id,
    shape_config,
    dr_boot_volume.id
    )

if launch_instance_from_boot_volume_response.data.lifecycle_state in ["UNKNOWN_ENUM_VALUE", "TERMINATING", "TERMINATED"]:
    print("Virtual Machine {} failed to launch to target child compartment {} in region {}.\nCheck the OCI Console for status and errors.\n".format(
        virtual_machine_name,
        target_child_compartment_name,
        dr_region
    ))
    raise RuntimeWarning("WARNING! Virtual Machine Failed to Launch.\n\n")
    
print("Attaching data volumes to the target virtual machine......\n")

for v in bv_list:
    attach_volume_response = attach_paravirtualized_volume(
        dr_compute_composite_client,
        AttachParavirtualizedVolumeDetails,
        launch_instance_from_boot_volume_response.data.id,
        v.id,
        v.display_name + "vol_attachment"
    )
    
    if attach_volume_response is None:
        raise RuntimeError("EXCEPTION! Unknown Error!")

print("The target virtual machine must now be fully stopped and restarted, please wait......\n")

stop_instance_response = stop_os_and_instance(
    dr_compute_composite_client,
    launch_instance_from_boot_volume_response.data.id
)
if stop_instance_response.lifecycle_state != "STOPPED":
    raise RuntimeError("EXCEPTION! Unknown Error")

dr_instance = GetInstance(
    dr_compute_client,
    target_child_compartment.id,
    virtual_machine_name
)
dr_instance.populate_instances()

start_instance_response = dr_instance.start_instance()

print("The virtual machine {} has been cloned to target child compartment {} in region {}\n".format(
    virtual_machine_name,
    target_child_compartment_name,
    dr_region
))

