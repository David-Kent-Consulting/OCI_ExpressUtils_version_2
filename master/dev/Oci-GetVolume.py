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

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-GetVolume.py : Usage\n\n" +
        "Oci-GetVolume.py [parent compartment] [child compartment] [volume name] [region]\n"+
        "[type --boot-volume/--volume] [optional argument]\n" +
        "Use case example 1 lists all data volumes within the specified child compartment by name:\n" +
        "\tOci-GetVolume.py admin_comp dbs_comp list_all_volumes 'us-ashburn-1' --volumes --name\n" +
        "Use case example 2 lists the specified boot volume within the child compartment:\n" +
        "\tOci-GetVolume.py admin_comp dbs_comp 'kentrmanp01 (Boot Volume)' 'us-ashburn-1' --boot-volume\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Usage Error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
volume_name                     = sys.argv[3]
region                          = sys.argv[4]
volume_type                     = sys.argv[5].upper()
if volume_type not in ["--BOOT-VOLUME", "--VOLUME"]:
    raise RuntimeWarning("INVALID VOLUME TYPE! Valid types are --boot-volume or --volume")
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

config["region"]                    = region # Must set the cloud region
identity_client                     = IdentityClient(config) # builds the identity client method, required to manage compartments
storage_client                      = BlockstorageClient(config)
compute_client                      = ComputeClient(config)

print("\n\nFetching tenant resource data, please wait......\n")
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

# Create a var based on volume_type, we are not concerned for mismatching on the volume_type.
# This is a way to reduce the logic complexity without generating an exception based on
# how the class is engineered.
if volume_type == "--BOOT-VOLUME":
    volume_list = volumes.boot_volumes
    volume = volumes.return_boot_volume_by_name(volume_name)
elif volume_type == "--VOLUME":
    volume_list = volumes.block_volumes
    volume = volumes.return_block_volume_by_name(volume_name)

# run through the logic
if len(sys.argv) == 6 and volume_name.upper() == "LIST_ALL_VOLUMES": # print everything
    print(volume_list)
elif len(sys.argv) == 7 and volume_name.upper() == "LIST_ALL_VOLUMES" and option == "--NAME":
    print("\n\nVOLUME_NAME")
    print("========================================")
    for vol in volume_list:
        print(vol.display_name)
elif len(sys.argv) == 7 and volume_name.upper() == "LIST_ALL_VOLUMES":
    print(
        "Invalid option for list_all_volumes. The only valid option is --name for this tool when listing all volumes.\n" +
        "Please try again with the correct option.\n\n"
    )
    raise RuntimeWarning("INVALID OPTION")

# now fetch the selected volume based on volume_type.
else:
    if len(sys.argv) == 6:
        print(volume)
    elif option == "--OCID":
        print(volume.id)
    elif option == "--NAME":
        print(volume.display_name)
    elif option == "--AVAILABILITY-DOMAIN":
        print(volume.availability_domain)
    elif option == "--LIFECYCLE-STATE":
        print(volume.lifecycle_state)
    elif option == "--SIZE":
        print(str(volume.size_in_gbs) + " Gbytes")
    elif option == "--SPEED":
        print(str(volume.vpus_per_gb) + " VPUS per GB")
    else:
        print(
            "\n\nWARNING! Invalid option. Valid options include:\n" +
            "\t--ocid\t\t\tPrints the volume's OCID\n" +
            "\t--name\t\t\tPrints the volume's display name\n" +
            "\t--availability-domain\tPrints the availability domain where the volume is in\n" +
            "\t--lifecycle-state\tPrints the lifecycle state of the volume\n" +
            "\t--size\t\t\tPrints the volume size in Gbytes\n" +
            "\t--speed\t\t\tPrints the speed performance setting of the volume in vpus per GB\n\n"+
            "Please try again with a correct option\n\n"
        )
        raise RuntimeWarning("INVALID OPTION")



