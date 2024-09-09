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
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.compute import GetShapes
from lib.compute import reboot_instance
from lib.subnets import GetPrivateIP
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks
from lib.volumes import attach_paravirtualized_volume
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeBackups
from lib.volumes import restore_block_volume
from lib.volumes import restore_boot_volume

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import BlockstorageClientCompositeOperations
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import AttachParavirtualizedVolumeDetails
from oci.core.models import VolumeSourceFromVolumeBackupDetails
from oci.core.models import BootVolumeSourceFromBootVolumeBackupDetails
from oci.core.models import VolumeSourceDetails
from oci.core.models import BootVolumeSourceDetails
from oci.core.models import CreateBootVolumeDetails
from oci.core.models import CreateVolumeDetails
from oci.core.models import CreateVnicDetails
from oci.core.models import InstanceSourceViaBootVolumeDetails
from oci.core.models import LaunchInstanceDetails
from oci.core.models import LaunchInstanceShapeConfigDetails

copywrite()
sleep(2)
if len(sys.argv) < 13 or len(sys.argv) > 14:
    print(
        "\n\nOci-RestoreVM.py : Usage\n\n" +
        "Oci-RestoreVM.py [parent compartment] [child compartment] [source VM] [region]\n" +
        "\t[new VM name] [target parent compartment] [target child compartment]\n" +
        "\t[target virtual cloud network] [target subnet] [target region] [Target AD number] [IP Address]\n\n"
        "Use case example restores the source VM to the specified target DR region\n" +
        "\tOci-RestoreVm.py acad_comp edu_comp edursrchp01 'us-ashburn-1' tstrestoret01 acad_comp \\\n" +
        "\t   edu_comp edudr_vcn edudr_sub01 'us-phoenix-1' 2 '10.1.0.100'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect usage")

# define global vars
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_machine_name                = sys.argv[3]
region                              = sys.argv[4]
vm_to_restore                       = sys.argv[5]
target_parent_compartment_name      = sys.argv[6]
target_child_compartment_name       = sys.argv[7]
target_virtual_cloud_network_name   = sys.argv[8]
target_subnet_name                  = sys.argv[9]
target_region                       = sys.argv[10]
target_ad_number                    = int(sys.argv[11])
target_ip_address                   = sys.argv[12]

if len(sys.argv) == 14:
    if sys.argv[13].upper() == "--JSON":
        option = sys.argv[13].upper()
    else:
        raise RuntimeWarning("INVALID OPTION! The only valid option is --json")
else:
    option = None

# used to determine if a supported shape is used with this codebase. We support VM.Standard2 and VM.Standard.E3.Flex
# This will determine the codeblock we run to create the VM instance.
standard_shapes                     = ["VM.Standard2.1", "VM.Standard2.2", "VM.Standard2.4", "VM.Standard2.8", "VM.Standard2.16", "VM.Standard2.24", "VM.Standard.E2.1", "VM.Standard.E2.2", "VM.Standard.E2.4", "VM.Standard.E2.8"]
flex_shapes                         = ["VM.Standard.E3.Flex", "VM.Standard.E4.Flex"]

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
storage_client                      = BlockstorageClient(config)
storage_composite_client            = BlockstorageClientCompositeOperations(storage_client)
compute_client                      = ComputeClient(config)

# set for the target region and instiate the environment
config["region"]                    = target_region
target_compute_client               = ComputeClient(config)
target_compute_composite_client     = ComputeClientCompositeOperations(target_compute_client)
target_network_client               = VirtualNetworkClient(config)
target_storage_client               = BlockstorageClient(config)
target_storage_composite_client     = BlockstorageClientCompositeOperations(target_storage_client)

print("\n\nGathering cloud data required for performing the restore request. Please wait......\n")
# get the parent compartment data
parent_compartments                 = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment                  = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the target parent compartment data
target_parent_compartments          = GetParentCompartments(
    target_parent_compartment_name,
    config,
    identity_client)
target_parent_compartments.populate_compartments()
target_parent_compartment = target_parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    target_parent_compartment,
    "Target parent compartment " + target_parent_compartment_name + " not found within tenancy " + config["tenancy"]
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

#############################################
# testing Hank Wojteczko starting 09.sep.2024
#############################################
compute_shapes = GetShapes(
    compute_client,
    child_compartment.id
)
compute_shapes.populate_shapes()
print(compute_shapes.shapes)
for s in compute_shapes.shapes:
    if s == 'resize_compatible_shapes':
        print(s)
exit(0)

#############################################
# end testing Hank Wojteczko starting 09.sep.2024
#############################################

# get the target child compartment
target_child_compartments = GetChildCompartments(
    target_parent_compartment.id,
    target_child_compartment_name,
    identity_client
)
target_child_compartments.populate_compartments()
target_child_compartment = target_child_compartments.return_child_compartment()
error_trap_resource_not_found(
    target_child_compartment,
    "Target child compartment " + target_child_compartment_name + " not found in parent compartment " +target_parent_compartment_name
)

# get the source VM data
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

# verify that a supported shape is used. Abort if not the case.
if vm_instance.shape not in flex_shapes: # or vm_instance.shape not in standard_shapes:
    print("Not a Flex shape, check standard shapes")
    if vm_instance.shape not in standard_shapes:
        print("Well, that did not work, invalid shape")
        raise RuntimeWarning("WARNING! Invalid or unsupported shape, please try again with a correct shape value.")

print("That worked, valid data found.\n")


# verify that the target VM does not exist
target_vm_instances = GetInstance(
    target_compute_client,
    target_child_compartment.id,
    vm_to_restore
)
target_vm_instances.populate_instances()
target_vm_instance = target_vm_instances.return_instance()
error_trap_resource_found(
    target_vm_instance,
    "Target VM instance " + vm_to_restore + " already present in compartment " + target_child_compartment_name + "within region " + target_region
)

# get the target virtual network data
virtual_networks = GetVirtualCloudNetworks(
    target_network_client,
    target_child_compartment.id,
    target_virtual_cloud_network_name
)
virtual_networks.populate_virtual_cloud_networks()
virtual_network = virtual_networks.return_virtual_cloud_network()
error_trap_resource_not_found(
    virtual_network,
    "Target virtual network " + target_virtual_cloud_network_name + " not found in compartment " + target_child_compartment_name + " within region " + target_region
)

# get the target subnet data
subnets = GetSubnet(
    target_network_client,
    target_child_compartment.id,
    virtual_network.id,
    target_subnet_name
)
subnets.populate_subnets()
subnet = subnets.return_subnet()
error_trap_resource_not_found(
    subnet,
    "Target subnetwork " + target_subnet_name + " not found within virtual cloud network " + target_virtual_cloud_network_name + " in region " + target_region
)

# check for dup IPs in target compartment
private_ip_addresses = GetPrivateIP(
    target_network_client,
    subnet.id
)
private_ip_addresses.populate_ip_addresses()
if private_ip_addresses.is_dup_ip(target_ip_address):
    warning_beep(2)
    print("\n\nIP address {} already assigned to resource in subnet {}. Duplicate IP addresses are not permitted.\n\n".format(
        target_ip_address,
        target_subnet_name
    ))
    raise RuntimeError("DUPLICATE IP ADDRESS VIOLATION")

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# Get the source VM boot and block volume data, we start by getting the block volumes.
print("Fetching volumes and backup snap data......\n")
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()

# next we sort through the boot volume attachments and pull the boot vol attachments for the source VM
boot_vol_attachments = get_boot_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id
    )

# now we get the boot volumes for the souerce VM
boot_volumes = []
for boot_vol_attachment in boot_vol_attachments:
    boot_volume = volumes.return_boot_volume(boot_vol_attachment.boot_volume_id)
    boot_volumes.append(boot_volume)

# next we get the block volume attachments
block_vol_attachments = get_block_vol_attachments(
    compute_client,
    vm_instance.availability_domain,
    child_compartment.id,
    vm_instance.id)

# finally we get the block volume data
block_volumes = []
for block_volume_attachment in block_vol_attachments:
    block_volume = volumes.return_block_volume(block_volume_attachment.volume_id)
    block_volumes.append(block_volume)

# We must get the volume backups from the target region
volume_backups = GetVolumeBackups(
    target_storage_client,
    child_compartment.id
)
volume_backups.populate_boot_volume_backups()
volume_backups.populate_block_volume_backups()

# The tricky part now is to remember to fetch the target backup using the volume_id object
# returned with the source VM instance. This is the entity relationship between these records.
boot_volume_backup = volume_backups.return_most_recent_active_boot_volume_backup(boot_vol_attachment.boot_volume_id)
error_trap_resource_not_found(
    boot_volume_backup,
    "No boot volume backups found in the target region " + target_region + " for the source VM " + virtual_machine_name
)

# do the same now for block volumes. Note there may be multiple block volumes per VM. So we check them all.
block_volume_backups = []
for block_volume in block_volumes:
    block_volume_backup = volume_backups.return_most_recent_active_block_volume_backup(block_volume.id)
    # only append with volume backups that have data, the class returns None if the lifecycle_state != AVAILABLE
    if block_volume_backup is not None:
        block_volume_backups.append(block_volume_backup)
    #block_volume_backups.append(volume_backups.return_most_recent_active_block_volume_backup(block_volume.id))

if len(block_volume_backups) != len(block_volumes):
    print(
        "\n\nWARNING! The most recent volume backups are inconsistent. The restore operation cannot be performed\n" +
        "until this is corrected. The most common cause of this issue is when the replication of volumes between\n" +
        "regions are inconsistent or incomplete or if a running backup job has not completed. Please inspect the\n" +
        "state of your backups and backup replications and try this operation again once the issue is resolved.\n\n"
    )
    raise RuntimeError("EXCEPTION! Volume backups do not match up with the VM instance's volumes.")


# get the target AD for the VM to restore to
# To do this, we must pass a tweaked version of the identity client that points to the target region.
# Recall config has already been set to the target region.
target_identitiy_client = IdentityClient(config)
target_ad_name = return_availability_domain(
    target_identitiy_client,
    target_child_compartment.id,
    target_ad_number)

# restore the boot volume backup to a new volume in the target location
print("\nRestoring the VM boot volume instance to the target compartment {}. Please wait......\n".format(
    target_child_compartment_name
))
new_volume = restore_boot_volume(
    target_storage_composite_client,
    BootVolumeSourceFromBootVolumeBackupDetails,
    BootVolumeSourceDetails,
    CreateBootVolumeDetails,
    vm_to_restore + " (Boot Volume)",
    target_ad_name,
    target_child_compartment.id,
    boot_volume.size_in_gbs,
    boot_volume_backup.id
    )
if new_volume is not None:
    if new_volume.lifecycle_state == "AVAILABLE":
        print("Volume restored, launching the restore VM instance {}. Please wait......\n".format(
            vm_to_restore
        ))
    else:
        print(new_volume)
        raise RuntimeError("EXCEPTION! Volume in an invalid state. Program aborting.")
else:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")

# prepare the launch instance details
if vm_instance.shape in flex_shapes:
    # run this code block for FLEX shapes
    launch_instance_details = LaunchInstanceDetails(
        availability_domain = new_volume.availability_domain,
        compartment_id = target_child_compartment.id,
        create_vnic_details = CreateVnicDetails(
            assign_public_ip = False,
            display_name = vm_to_restore + "_vnic_00",
            hostname_label = vm_to_restore,
            private_ip = target_ip_address,
            subnet_id = subnet.id
        ),
        display_name = vm_to_restore,
        shape = vm_instance.shape,
        shape_config = LaunchInstanceShapeConfigDetails(
            ocpus = vm_instance.shape_config.ocpus,
            memory_in_gbs = vm_instance.shape_config.memory_in_gbs
        ),
        source_details = InstanceSourceViaBootVolumeDetails(
            source_type = "bootVolume",
            boot_volume_id = new_volume.id
        )
    )
else:
    #run this code if standard shape
     launch_instance_details = LaunchInstanceDetails(
        availability_domain = new_volume.availability_domain,
        compartment_id = target_child_compartment.id,
        create_vnic_details = CreateVnicDetails(
            assign_public_ip = False,
            display_name = vm_to_restore + "_vnic_00",
            hostname_label = vm_to_restore,
            private_ip = target_ip_address,
            subnet_id = subnet.id
        ),
        display_name = vm_to_restore,
        shape = vm_instance.shape,
        source_details = InstanceSourceViaBootVolumeDetails(
            source_type = "bootVolume",
            boot_volume_id = new_volume.id
        )
    )

# Launch the instance
print("Launching the VM instance......\n")

launch_instance_response = target_compute_composite_client.launch_instance_and_wait_for_state(
    launch_instance_details = launch_instance_details,
    wait_for_states = ["RUNNING", "TERMINATED", "UNKNOWN_ENUM_VALUE"]
).data


if launch_instance_response.lifecycle_state != "RUNNING":
    print("VM instance {} failed to start within compartment {}. Please check the OCI console for details.\n".format(
        vm_to_restore,
        target_child_compartment_name
    ))
    raise RuntimeError("EXCEPTION! VM instance failed to start.")
else:
    print("VM instance {} has started and is in a run state. Restoring data disks now. Please wait......\n".format(
        vm_to_restore
    ))

# perform a restore operation on each of the data disks if present
if len(block_volumes) > 0:
    new_block_volumes = []
    count = 0
    for block_volume_backup in block_volume_backups:
        for block_volume in block_volumes:
            if block_volume.id == block_volume_backup.volume_id:
                results = restore_block_volume(
                    target_storage_composite_client,
                    VolumeSourceFromVolumeBackupDetails,
                    VolumeSourceDetails,
                    CreateVolumeDetails,
                    launch_instance_response.display_name + "datadisk_" + str(count),
                    launch_instance_response.availability_domain,
                    target_child_compartment.id,
                    block_volume.size_in_gbs,
                    block_volume_backup.id
                )
                if results is None:
                    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
                else:
                    new_block_volumes.append(results)
                    count += 1

    # attach the volumes to the restored VM instance
    print("Attaching data disks to VM instance {}. Please wait......\n".format(
        vm_to_restore
    ))
    new_volume_attachments = []
    for new_block_volume in new_block_volumes:
        new_volume_attachment = attach_paravirtualized_volume(
            target_compute_composite_client,
            AttachParavirtualizedVolumeDetails,
            launch_instance_response.id,
            new_block_volume.id,
            new_block_volume.display_name + "_attachment"
        )
        new_volume_attachments.append(new_volume_attachment)
else:
    print("There are no data disks to restore. Proceeding to the next task.\n")
# end if len(block_volumes) > 0

# restart the VM instance
print("VM instance {} successfully restored. A restart is required, restarting the VM. Please wait.......\n".format(
    vm_to_restore
))
results = reboot_instance (
    target_compute_composite_client,
    launch_instance_response.id
)
sleep(60)
print("Restarted the VM instance, printing the results below......\n")
sleep(5)
if option == "--JSON":
    print(results)
else:

    header = [
        "COMPARTMENT",
        "VM",
        "RECOVERY ACTION",
        "LIFECYLE STATE",
        "AVAILABILITY DOMAIN",
        "FAULT DOMAIN",
        "SHAPE",
        "OCPUS",
        "MEMORY",
        "REGION"
    ]
    data_rows = [[
        target_child_compartment_name,
        results.display_name,
        results.availability_config.recovery_action,
        results.lifecycle_state,
        results.availability_domain,
        results.fault_domain,
        results.shape,
        results.shape_config.ocpus,
        results.shape_config.memory_in_gbs,
        target_region
    ]]
    print(tabulate(data_rows, headers = header, tablefmt = "simple"))

# end of Oci-RestoreVM.py
