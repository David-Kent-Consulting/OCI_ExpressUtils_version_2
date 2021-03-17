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
import platform
import resource
import sys
from tabulate import tabulate
from time import sleep


# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import is_int
from lib.general import test_free_mem_1gb
from lib.general import warning_beep
from lib.backups import GetVolumeBackupItems
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.volumes import GetVolumes
from lib.volumes import GetVolumeAttachment

# required DKC modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient

###########################################################################################
#                                   functions                                             #
###########################################################################################
def print_invalid_msg():
    warning_beep(2)
    print(
        "INVALID OPTION! Valid options include:\n\n" +
        "\t--date ddmmyyyy\t\tAll backups for the specified date is returned.\n" +
        "\t\t\t\tThe date must be 8 digits in day, month, year format.\n" +
        "\t--name 'name of item'\tThe name of the backup item to report on\n" +
        "\t--json\t\t\tPrint outut for all backups in JSON format and supress other output\n\n" +
        "Please try again with a correct option.\n\n"
    )
    raise RuntimeWarning("INVALID OPTION")

# end function print_invalid_msg()

###########################################################################################
#                                   end functions                                         #
###########################################################################################

if len(sys.argv) < 7 or len(sys.argv) > 9:
    print(
        "\n\nOci-GetVolumeBackupItems.py : Usage\n\n" +
        "Oci-GetVolumeBackupItems.py [parent compartment] [child compartment] [volume type ] [volume]\n" +
        "[region] [dr region] [optional parameter with value]\n\n" +
        "Use case example 1 reports all backup items for the specified volume within the specified compartment:\n" +
        "\tOci-GetVolumeBackupItems.py acad_comp math_comp --volume algebrap01_datadisk_1 'us-ashburn-1' 'us-phoenix-1'\n" +
        "Use case example 2 reports all backups for the specified volume on the specified day:\n" +
        "\tOci-GetVolumeBackup.py acad_comp math_comp --volume calcp01_datadisk_1 'us-ashburn-1' 'us-phoenix-1' -day 26022021\n" +
        "Use case example 3 reports all detail on the specified backup object:\n" +
        "\tOci-GetVolumeBackup.py acad_comp math_comp --boot-volume 'trigp01 (Boot Volume)' 'us-ashburn-1' 'us-phoenix-1' \\\n" +
        "\t -name 'Auto-backup for 2021-03-08 05:00:00 via policy: math_prod_bk_policy'\n" +
        "Use case exmaple 4 reports all backups for the volume in JSON format and supresses other output:\n" +
        "\tOci-GetVolumeBackupItems.py acad_comp math_comp --volume algebrap01_datadisk_1 'us-ashburn-1' 'us-phoenix-1' --json\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    warning_beep(1)
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]

if sys.argv[3].upper() not in ["--BOOT-VOLUME", "--VOLUME"]:
    raise RuntimeWarning("INVALID VALUE! The only valid value for volume type is --BOOT-VOLUME or --VOLUME")
else:
    volume_type                     = sys.argv[3].upper()

volume_name                         = sys.argv[4]
region                              = sys.argv[5]
dr_region                           = sys.argv[6]

if len(sys.argv) == 7:
    option = None
elif len(sys.argv) == 8:
    option                          = sys.argv[7].upper()

else:
    option                          = sys.argv[7].upper()
    option_value                    = sys.argv[8]

header = [
    "COMPARTMENT",
    "VOLUME",
    "BACKUP_SET",
    "DATE CREATED",
    "EXPIRATION DATE",
    "LIFECYCLE STATE",
    "REGION"
]

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
correct_region = False
for rg in regions:
    if rg.name == dr_region:
        correct_region = True
if not correct_region:
    print("\n\nWARNING! - Disaster Recovery Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching and validating tenancy resource data......\n")

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client = ComputeClient(config)
storage_client = BlockstorageClient(config)
config["region"] = dr_region # reset to DR region for pulling DR backup copies
dr_storage_client = BlockstorageClient(config)

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

# Get the source VM boot and block volume data, we start by getting the block volumes.
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id)
volumes.populate_boot_volumes()
volumes.populate_block_volumes()

if volume_type == "--BOOT-VOLUME":
    
    volume = volumes.return_boot_volume_by_name(volume_name)
    error_trap_resource_not_found(
        volume,
        "Volume " + volume_name + " not found within compartment " + child_compartment_name + " in region " + region
    )

elif volume_type == "--VOLUME":
    
    volume = volumes.return_block_volume_by_name(volume_name)
    error_trap_resource_not_found(
        volume,
        "Volume " + volume_name + " not found within compartment " + child_compartment_name + " in region " + region
    )

else:
    
    raise RuntimeWarning("INVALID VALUE! Value for volume_type must be --BOOT-VOLUME OR --VOLUME ")

if not test_free_mem_1gb():
    raise RuntimeError("EXCEPTION! INSUFFICIENT MEMORY")

if option != "--JSON":
    print("Fletching and validating backups......")

backup_items = GetVolumeBackupItems(
    storage_client,
    dr_storage_client,
    child_compartment.id,
    volume_type,
    volume.id
)
backup_items.populate_backup_items()

# run through the options choice and return report based on input
if len(sys.argv) == 7:


    data_rows = []

    if backup_items.return_all_backup_items() is not None:
        for backup_item in backup_items.return_all_backup_items():

            if backup_item.expiration_time is None:
                expiration_date = "INFINITE"
            else:
                expiration_date = backup_item.expiration_time.ctime()

            data_row = [
                child_compartment_name,
                volume_name,
                backup_item.display_name,
                backup_item.time_created.ctime(),
                expiration_date,
                backup_item.lifecycle_state,
                region
            ]
            data_rows.append(data_row)

    if backup_items.return_all_dr_backup_items() is not None:
        for backup_item in backup_items.return_all_dr_backup_items():

            if backup_item.expiration_time is None:
                expiration_date = "INFINITE"
            else:
                expiration_date = backup_item.expiration_time.ctime()

            data_row = [
                child_compartment_name,
                volume_name,
                backup_item.display_name,
                backup_item.time_created.ctime(),
                expiration_date,
                backup_item.lifecycle_state,
                dr_region
            ]
            data_rows.append(data_row)
    
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

    

elif len(sys.argv) == 8 and option == "--JSON":

    print(backup_items.return_all_backup_items())
    print(backup_items.return_all_dr_backup_items())

elif len(sys.argv) == 9:

    if option == "--DATE":

        print("date logic")
        # print(option_value[:2])       # returns the day 2 digits
        # print(option_value[2:4])      # returns the month 2 digits
        # print(option_value[4:8:1])    # returns the year 4 digits
        # run through the logic to ensure a correctly formatted data
        if is_int(option_value):
            print("its all numbers")
            day_of_month  = int(option_value[:2])
            month_of_year = int(option_value[2:4])
            year          = int(option_value[4:8:1])
            if day_of_month > 0 and day_of_month < 32:
                print("day of month good")
                if month_of_year > 0 and month_of_year < 12:
                    if year > 1999:

                        data_rows = []
                        backup_item = backup_items.return_backups_this_day(
                            option_value[:2],
                            option_value[2:4],
                            option_value[4:8:1]
                        )
                        if backup_item is not None:

                            if backup_item.expiration_time is None:
                                expiration_date = "INFINITE"
                            else:
                                expiration_date = backup_item.expiration_time.ctime()

                            data_row = [
                                child_compartment_name,
                                volume_name,
                                backup_item.display_name,
                                backup_item.time_created.ctime(),
                                expiration_date,
                                backup_item.lifecycle_state,
                                dr_region
                            ]
                            data_rows.append(data_row)
                        backup_item = backup_items.return_dr_backups_this_day(
                            option_value[:2],
                            option_value[2:4],
                            option_value[4:8:1]
                        )

                        if backup_item is not None:
                        
                            if backup_item.expiration_time is None:
                                    expiration_date = "INFINITE"
                            else:
                                expiration_date = backup_item.expiration_time.ctime()
    
                                data_row = [
                                    child_compartment_name,
                                    volume_name,
                                    backup_item.display_name,
                                    backup_item.time_created.ctime(),
                                    expiration_date,
                                    backup_item.lifecycle_state,
                                    dr_region
                                ]
                                data_rows.append(data_row)

                        print(tabulate(data_rows, headers = header, tablefmt = "grid"))

                    else:
                        raise RuntimeWarning("INVALID VALUE! Year must be a 4 digit value and be greater than 1999")
                else:
                    raise RuntimeWarning("INVALID VALUE! - Month of year must be a two digit between 01 and 12")
            else:
                warning_beep(2)
                raise RuntimeWarning("INVALID VALUE! - Day of month must be a 2 digit value day between 01 and 31")
        else:
            warning_beep(2)
            raise RuntimeWarning("INVALID VALUE! - Date must be a 2 digit day, 2 digit month, and a 4 digit year")


    elif option == "--NAME":

        backup_item = backup_items.return_backup_item(option_value)

        if backup_item is None:
            backup_item = backup_items.return_dr_backup_item(option_value)
            if backup_item is None:
                data_rows = []
            else:

                if backup_item.expiration_time is None:
                    expiration_date = "INFINITE"
                else:
                    expiration_date = backup_item.expiration_time.ctime()

                data_rows = [[
                    child_compartment_name,
                    volume_name,
                    backup_item.display_name,
                    backup_item.time_created.ctime(),
                    expiration_date,
                    backup_item.lifecycle_state,
                    region
                ]]
                
        else:
            if backup_item.expiration_time is None:
                expiration_date = "INFINITE"
            else:
                expiration_date = backup_item.expiration_time.ctime()

            data_rows = [[
                child_compartment_name,
                volume_name,
                backup_item.display_name,
                backup_item.time_created.ctime(),
                expiration_date,
                backup_item.lifecycle_state,
                region
            ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\nBackup Item ID :\t" + backup_item.id)

    else:
        print_invalid_msg()

else:

    print_invalid_msg()

