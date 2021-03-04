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
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.volumes import GetVolumes

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient


if len(sys.argv) < 5 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetVolume.py : Usage\n\n" +
        "Oci-GetVolume.py [parent compartment] [child compartment] [volume name] [region] [optional argument]\n\n" +
        "Use case example 1 lists all volumes within the specified child compartment:\n" +
        "\tOci-GetVolume.py admin_comp dbs_comp list_all_volumes 'us-ashburn-1'\n" +
        "Use case example 2 lists the specified boot volume within the child compartment:\n" +
        "\tOci-GetVolume.py admin_comp dbs_comp 'kentrmanp01 (Boot Volume)' 'us-ashburn-1' --boot-volume\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Usage Error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
volume_name                     = sys.argv[3]
region                          = sys.argv[4]
option                          = None # required for logic
if len(sys.argv) > 5:
    volume_type = sys.argv[5].upper()
    if len(sys.argv) == 7:
        option = sys.argv[6].upper()

if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching tenant resource data, please wait......\n")



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
compute_client                      = ComputeClient(config)

# get the parent compartment data
parent_compartments                 = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment                  = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
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

# get the availability domains
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# get volume data
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id
)
# populate class
volumes.populate_boot_volumes()
volumes.populate_block_volumes()


# run through the logic
if sys.argv[3].upper() == "LIST_ALL_VOLUMES":
    header = [
        "COMPARTMENT",
        "VOLUME NAME",
        "VOLUME TYPE",
        "SIZE GB",
        "PERFORMANCE SETTING",
        "LIFECYCLE STATE",
        "REGION"
    ]
    data_rows = []
    # parse through boot volumes, then data volumes
    if volumes.return_all_boot_volunes() is not None:
        for bv in volumes.return_all_boot_volunes():
            if bv.vpus_per_gb == 0:
                performance_setting = "LOW"
            elif bv.vpus_per_gb == 10:
                performance_setting = "BALANCED"
            elif bv.vpus_per_gb == 20:
                performance_setting = "HIGH"
            data_row = [
                child_compartment_name,
                bv.display_name,
                "BOOT",
                performance_setting,
                bv.lifecycle_state,
                region
            ]
            data_rows.append(data_row)

    if volumes.return_all_block_volumes() is not None:
        for bv in volumes.return_all_block_volumes():
            if bv.vpus_per_gb == 0:
                performance_setting = "LOW"
            elif bv.vpus_per_gb == 10:
                performance_setting = "BALANCED"
            elif bv.vpus_per_gb == 20:
                performance_setting = "HIGH"
            data_row = [
                child_compartment_name,
                bv.display_name,
                "DATA",
                performance_setting,
                bv.lifecycle_state,
                region
            ]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

elif len(sys.argv) > 5:

    # get the volume type based on user input
    if volume_type == "--BOOT-VOLUME":
        volume = volumes.return_boot_volume_by_name(volume_name)
    elif volume_type == "--VOLUME":
        volume = volumes.return_block_volume_by_name(volume_name)
    error_trap_resource_not_found(
        volume,
        "Volume " + volume_name + " of type " + volume_type + " not found in compartment " + child_compartment_name + "in region " + region
    )

    # it's all good, lets do the logic to return the results
    if volume.vpus_per_gb == 0:
        performance_setting = "LOW"
    elif volume.vpus_per_gb == 10:
        performance_setting = "BALANCED"
    elif volume.vpus_per_gb == 20:
        performance_setting = "HIGH"


    if len(sys.argv) == 6: # no options provided, just print the volume summary

        header = [
            "COMPARTMENT",
            "AVAILABILITY DOMAIN",
            "VOLUME",
            "TYPE",
            "SIZE",
            "PERFORMANCE SETTING",
            "LIFECYCLE STATE",
            "REGION"
        ]

        if volume_type == "--BOOT-VOLUME":
            v_type = "BOOT VOLUME"
        elif volume_type == "--VOLUME":
            v_type = "VOLUME"
        
        data_rows = [[
            child_compartment_name,
            volume.availability_domain,
            volume.display_name,
            v_type,
            volume.size_in_gbs,
            performance_setting,
            volume.lifecycle_state,
            region
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))

    elif option == "--OCID":
        print(volume.id)
    elif option == "--NAME":
        print(volume.display_name)
    elif option == "--LIFECYCLE-STATE":
        print(volume.lifecycle_state)
    elif option == "--PERFORMANCE-SETTING":
        print(performance_setting)
    elif option == "--SIZE":
        print(volume.size_in_gbs)
    elif option == "--JSON":
        print(volume)
    else:
        print(
            "\n\nINVALID OPTION! Valid options are:\n\n" +
            "\t--ocid\t\t\tPrint the OCID of the volume\n" +
            "\t--name\t\t\tPrint the volume name\n" +
            "\t--lifecycle-state\tPrint the volume's lifecycle state\n" +
            "\t--performance-setting\tPrint the volume's performance setting\n" +
            "\t--size\t\t\tPrint the volume size in Gbytes\n" +
            "\t--json\t\t\tPrint all resource data in JSON format and surpresses other output\n\n" +
            "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )
        raise RuntimeWarning("INVALID OPTION!")

else:
    raise RuntimeWarning("MISSING ARGUMENT! Volume type must be supplied and must be --boot-vol or --volume")


# # now fetch the selected volume based on volume_type.
# else:
#     if len(sys.argv) == 6:
#         print(volume)
#     elif option == "--OCID":
#         print(volume.id)
#     elif option == "--NAME":
#         print(volume.display_name)
#     elif option == "--AVAILABILITY-DOMAIN":
#         print(volume.availability_domain)
#     elif option == "--LIFECYCLE-STATE":
#         print(volume.lifecycle_state)
#     elif option == "--SIZE":
#         print(str(volume.size_in_gbs) + " Gbytes")
#     elif option == "--SPEED":
#         print(str(volume.vpus_per_gb) + " VPUS per GB")
#     else:
#         print(
#             "\n\nWARNING! Invalid option. Valid options include:\n" +
#             "\t--ocid\t\t\tPrints the volume's OCID\n" +
#             "\t--name\t\t\tPrints the volume's display name\n" +
#             "\t--availability-domain\tPrints the availability domain where the volume is in\n" +
#             "\t--lifecycle-state\tPrints the lifecycle state of the volume\n" +
#             "\t--size\t\t\tPrints the volume size in Gbytes\n" +
#             "\t--speed\t\t\tPrints the speed performance setting of the volume in vpus per GB\n\n"+
#             "Please try again with a correct option\n\n"
#         )
#         raise RuntimeWarning("INVALID OPTION")



