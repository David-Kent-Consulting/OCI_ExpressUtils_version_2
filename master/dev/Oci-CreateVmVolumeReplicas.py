#!/usr/bin/python3

# Copyright 2019 – 2021 David Kent Consulting, Inc.
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
from lib.general import warning_beep
from lib.backups import add_volume_to_backup_policy
from lib.backups import GetBackupPolicies
from lib.backups import delete_volume_backup_policy
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
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
from oci.core import ComputeClient

from oci.core.models import UpdateBootVolumeDetails
from oci.core.models import BootVolumeReplicaDetails
from oci.core.models import UpdateVolumeDetails
from oci.core.models import BlockVolumeReplicaDetails

copywrite()

if len(sys.argv) != 6:
    print(
        "\n\nOci-CreateVmVolumeReplicas.py : Usage\n\n" +
        "Oci-CreateVmVolumeReplicas.py [parent compartment] [child compartment] [VM] [region] [dr region]\n" +
        "Usage example creates replica copies of the VM's boot and block volumes from the primary region\n" +
        "to the disaster recovery region specified in the command arguments:\n" +
        "\tOci-CreateVmVolumeReplicas.py admin_comp auto_comp kentanst01 'us-ashburn-1' 'us-phoenix-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect usage")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_machine_name                = sys.argv[3]
region                              = sys.argv[4]
dr_region                           = sys.argv[5]

# instiate the environment and validate the regions

print("\n\nValidating the cloud tenancy and other resources are available.......\n")
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
storage_client = BlockstorageClient(config) # builds the volume client method, required to manage block volume resources

# validate the parent and child compartments
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

# Validate the subscribed regions
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

# Get the availability domains for the VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

print("Tenancy and regions verified, fetching VM and storage resource data......\n")

# make sure the VM we are looking for exists
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name,
    
    
)
vm_instances.populate_instances()
vm_instance = vm_instances.return_instance()

error_trap_resource_not_found(
    virtual_machine_name,
    "Virtual machine instance " + virtual_machine_name + " not found within compartment " + child_compartment_name + " in region " + region
)

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

# get the disk volumes
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

print("Creating the volume replicas for virtual machine {} from region {}\n to region {}......\n".format(
          virtual_machine_name,
          region,
          dr_region
      ))

# Create replicas if they do not exist in dr_region

for bv in boot_volumes:
    if None == bv.boot_volume_replicas:
        '''
        we have to create the text string for the availability domain where the
        replica is to be created. This consists of the availability domain
        of the source domain, aka the first 4 chars of the volume's availability
        domain, plus a :, (we get that from the 1st 5 chars of bv.availability_domain),
        plus the region key (we get that from replica_region.key), plus the string
        "-AD-", plus the last char of bv (bv.availability_domain[-1])
        
        This same logic will be applied for creating block volume replicas.
        '''
        create_bootvol_replica_response = create_bootvol_replica(
            storage_client,
            UpdateBootVolumeDetails,
            BootVolumeReplicaDetails,
            bv.id,
            (bv.availability_domain[:5] + replica_region.key + "-AD-" + bv.availability_domain[-1]),
            bv.display_name
        )

        if create_bootvol_replica_response.data is None:
            raise RuntimeError("EXCEPTION! Unknown Error")
        else:
            print("Replication for boot volume {} enabled to DR region {}\n".format(
                bv.display_name,
                dr_region
            ))
    
    else:

        print("Boot volume {} already replicating to DR region {}, skipping\n".format(
            bv.display_name,
            dr_region
        ))

for v in block_volumes:
    if None == v.block_volume_replicas:
        '''
        we have to create the text string for the availability domain where the
        replica is to be created. This consists of the availability domain
        of the source domain, aka the first 4 chars of the volume's availability
        domain, plus a :, (we get that from the 1st 5 chars of bv.availability_domain),
        plus the region key (we get that from replica_region.key), plus the string
        "-AD-", plus the last char of bv (bv.availability_domain[-1])
        
        This same logic will be applied for creating boot volume replicas.
        '''
        create_vol_replica_response = create_vol_replica(
            storage_client,
            UpdateVolumeDetails,
            BlockVolumeReplicaDetails,
            v.id,
            (v.availability_domain[:5] + replica_region.key + "-AD-" + v.availability_domain[-1]),
            v.display_name
        )
        
        if create_vol_replica_response.data is None:
            raise RuntimeError("EXCEPTION! Unknown Error")
        else:
            print("Replication for volume {} enabled to DR region {}\n".format(
                v.display_name,
                dr_region
            ))
    
    else:

        print("Volume {} already replicating to DR region {}, skipping\n".format(
            bv.display_name,
            dr_region
        ))

print("All volumes for virtual machine {} are now replicated between region {}\n and DR region {}.\n\n".format(
    virtual_machine_name,
    region,
    dr_region
))

