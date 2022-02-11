#!/usr/bin/python3

# Copyright 2019 – 2022 David Kent Consulting, Inc., Kent Cloud Solutions, Inc.
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

The purpose of this utility is to manage disk SNAP backups in OCI
outside of the tools provided for in the OCI console. We recommend
that this tool only be used on a case-by-case basis, and rarely,
if at all. The initial use case for this tool is to manage OEM
backups. We must backup OEM cold, aka shutdown the database and
other services, then run the disk SNAPS, and then restart OEM.
This is unfortunately necessary since Oracle has placed restrictions
both within OCI and in the OEM appliance build that render tools
such as RMAN, cp, and zip useless. As of the time of the creation of
this utility, 11-feb-2022, it is not possible to copy large numbers
of files or any file larger than 1GB from the OEM boot volume. We
suspect that Oracle has customized the kernel, but do not know that
with certainty. What we do know with certainty is that the OEM
marketplace image has restrictions enabled that prevent disk
and SNAP replication to another region. We also know that it is
not possible to define an expiration date when creating a disk
SNAP. Therefore, we must manage expiring SNAP objects when creating
them outside of the tools in the console, or via API, when using
backup schedules and assigning those schedules to storage.

Simply put, run the tool and it:

1) Builds a list of all backup SNAPs in the compartment/region
2) Looks for the last backup SNAP with the same name as the
   new backup SNAP, and if it exists, removes it.
3) Creates the new SNAP.

This utility can be run with the --silent option to suppress
all program output except when an exception is raised.

'''

# required system modules
from datetime import date
import calendar
import os.path
import platform
import resource
import sys
from tabulate import tabulate
from time import sleep


# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import test_free_mem_1gb
from lib.general import warning_beep
from lib.backups import create_bootvolume_backup
from lib.backups import create_volume_backup
from lib.backups import delete_bootvolume_backup
from lib.backups import delete_volume_backup
from lib.backups import get_compartment_backup_data
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.compute import get_boot_vol_attachments
from lib.compute import GetInstance
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeAttachment

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient
from oci.core.models import CreateBootVolumeBackupDetails
from oci.core.models import CreateVolumeBackupDetails

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "Oci-BackupVmDisks.py : Usage\n\n" +
        "Oci-BackupVmDisks.py [parent compartment] [child compartment] [vm name] [region]\n\n" +
        "Use case example backs up all disks attached to the specified VM within the specified region\n" +
        "in silent mode, and will not send output unless an exception is raised. Do not use the\n" +
        "--silent option if you wish to see output.\n\n" +
        "\tOci-BackupVmDisk.py admin_comp oem_comp 'EMS-OMS1' 'us-ashburn-1' --silent\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("INVALID USAGE\n\n")

if len(sys.argv) == 6 and sys.argv[5].upper() != "--SILENT":
    raise RuntimeWarning("WARNING! INVALID OPTION\n\n")
elif len(sys.argv) == 6 and sys.argv[5].upper() == "--SILENT":
    option = True
else:
    option = False

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
virtual_machine_name                    = sys.argv[3]
region                                  = sys.argv[4]

if not option:
    copywrite()
    print("\nGathering tenancy data, please wait......\n")

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

config["region"] = region # dictionary object
identity_client = IdentityClient(config) # identity instance
compute_client = ComputeClient(config) # compute instance
storage_client = BlockstorageClient(config) # storage instance primary region

# Get the parent compartment
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
    "Child compartment " + child_compartment_name + " not found within parent compartment " + parent_compartment_name
)

# Get the availability domains for the source VM
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id)

# Get the VM data but do not pass a VM instance name, we do not need it in this use case
vm_instances = GetInstance(
    compute_client,
    child_compartment.id,
    virtual_machine_name
)
vm_instances.populate_instances()

'''
those of you new to coding please make note of the codification standard below for
print when passing vars within the code. This is a python 1.x method. There is the
more terse usage. We do not employ it since the python 1.x syntax is more readable.
Also note how we format the vars within format(). This again is part of our
codification standard and is done for read ability purposes.
'''

if not option:
    print("Gathering all backup data for child compartment {} within region {}\n".format(
        child_compartment_name,
        region
    ))

'''

Fetch all compartment backup data. The underlying function uses the page method in the OCI REST APIs since
the amount of data is copious. Your docker image instance must reserve 1GB RAM for this to work. Begin
by checking this. The function get_compartment_backup_data is complex and required many methods and
functions to run. We ensure this requirement is met by requiring you to pass them to the function.

Explanation of required methods and where you can find them are:

    compute_client                 You should instiate in accordance with KENT codification standards
    get_block_vol_attachments      import from lib.storage
    get_boot_vol_attachments       import from lib.storage
    storage_client                 You should instiate in accordance with KENT codification standards
    child_compartment              You should instiate in accordance with KENT codification standards
    vm_instances                   You should instiate in accordance with KENT codification standards
    
Be sure to read the function backups.get_compartment_backup_data() and get familiar with it before
calling this function. There are comments in the code that explains what it does.

'''
if not test_free_mem_1gb():
    raise RuntimeError("ERROR! INSUFFICENT MEMORY\n\n")
else:
    
    all_compartment_backup_data = get_compartment_backup_data(
        compute_client,
        get_block_vol_attachments,
        get_boot_vol_attachments,
        storage_client,
        child_compartment,
        vm_instances
        )

# set today's backup set name, This will be used to remove old backups and create new ones
# Yes, I could have collapsed the 3 lines into one line, but why make the code difficult
# to understand?
current_time_stamp              = date.today()
day_of_month                    = current_time_stamp.day
backup_prefix                   = "_backup_day_of_month_" + str(day_of_month)
bootvolume_backup_sets          = []
volume_backup_sets              = []

for vm in all_compartment_backup_data:
    if vm["vm_name"] == virtual_machine_name:
        for boot_volume in vm["boot_volumes"]:
            bootvolume_backup_set_name = {
                "boot_volume_id"    : "",
                "display_name"      : ""
            }
            bootvolume_backup_set_name["boot_volume_id"]   = boot_volume.id
            bootvolume_backup_set_name["display_name"]     = boot_volume.display_name + backup_prefix
            bootvolume_backup_sets.append(bootvolume_backup_set_name)

        for volume in vm["volumes"]:
            volume_backup_set_name = {
                "volume_id"         : "",
                "display_name"      : ""
            }
            volume_backup_set_name["volume_id"]            = volume.id
            volume_backup_set_name["display_name"]         = volume.display_name + backup_prefix
            volume_backup_sets.append(volume_backup_set_name)

# remove comments for debugging, otherwise leave commented out, we will remove these comments
# when testing is completed.
# print(bootvolume_backup_sets)
# print(volume_backup_sets)

if not option:
    print("Removing obsolete backups for VM {} in child compartment {} within region {}......\n".format(
        virtual_machine_name,
        child_compartment_name,
        region
    ))

# First check to see if an old backup snap of the same name exists, and if it does, remove it
for vm in all_compartment_backup_data:
    if vm["vm_name"] == virtual_machine_name:
        
        # first part checks the bootvol backup list
        for bootvbk in vm["boot_volume_backups"]:
            for bootvolume_backup_set_name in bootvolume_backup_sets:
                '''
                The logic necessitates that we abort if the backup snap is in any of the following states.
                This elininates risk of duplicates if the resource is creating and the code called again,
                or if the SNAP is faulty. If the SNAP is faulty, we do not want the code to run. Instead,
                we want the underlying issue to be resolved ASAP. Same logic repeated below.
                '''
                if bootvolume_backup_set_name["display_name"] == bootvbk.display_name and bootvbk.lifecycle_state in [
                "CREATING", "FAULTY", "UNKNOWN_ENUM_VALUE"]:
                    raise RuntimeError("ERROR! BOOT VOLUME BACKUP NOT IN AVAILABLE LIFECYCLE STATE\n\n")
                # do not consider other lifecycle states other than AVAILABLE
                elif bootvolume_backup_set_name["display_name"] == bootvbk.display_name and bootvbk.lifecycle_state == "AVAILABLE":
                    delete_bootvolume_backup(
                        storage_client,
                        bootvbk.id)
        
        # next do the same for block volumes
        for blockvbk in vm["vol_backups"]:
            for volume_backup_set_name in volume_backup_sets:
                if volume_backup_set_name["display_name"] == blockvbk.display_name and blockvbk.lifecycle_state in [
                "CREATING", "FAULTY", "UNKNOWN_ENUM_VALUE"]:
                    raise RuntimeError("ERROR! VOLUME BACKUP NOT IN AVAILABLE LIFECYCLE STATE\n\n")
                elif volume_backup_set_name["display_name"] == blockvbk.display_name and blockvbk.lifecycle_state == "AVAILABLE":
                    delete_volume_backup(
                        storage_client,
                        blockvbk.id)

'''
This logic parses down the dictionary object volume_set previously created and passes to
the function create_volume_backup the volume OCID and desired string for display_name.
The OCI REST service will create the SNAP. We choose to not wait for the results but
do receive the full OCI REST response from the function. Note the API does not have logic
do remove old backups. This is why we preceed this logic with code that grooms old
backup SNAPs.
'''

for volume_set in volume_backup_sets:
    create_volume_backup(
    CreateVolumeBackupDetails,
    storage_client,
    volume_set["volume_id"],
    volume_set["display_name"],
    day_of_month)

if not option:
    print("Creating backup SNAP copies of all storage attached to VM {}\n".format(
        virtual_machine_name
    ))

'''
The same logic as used in the above, except this time we do it for boot volumes.
OCI APIs require a different call for boot volumes versus volumes even though
the logic is identical in both cases.
'''

for boot_volume_set in bootvolume_backup_sets:
    create_bootvolume_backup(
        CreateBootVolumeBackupDetails,
        storage_client,
        boot_volume_set["boot_volume_id"],
        boot_volume_set["display_name"],
        day_of_month
    )

if not option:
    print("Backups now in a CREATING state for virtual machine {} in child compartment {} wirthin region {}\n".format(
        virtual_machine_name,
        child_compartment_name,
        region
    ))

# end of program