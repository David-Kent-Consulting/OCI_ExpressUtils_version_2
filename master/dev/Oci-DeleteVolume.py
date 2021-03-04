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
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import get_block_vol_attachments
from lib.volumes import attach_iscsi_volume
from lib.volumes import attach_paravirtualized_volume
from lib.volumes import delete_volume
from lib.volumes import GetVolumeAttachment
from lib.volumes import GetVolumes

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import BlockstorageClientCompositeOperations

copywrite()
sleep(2)
if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-DeleteVolume.py : Usage\n\n" +
        "Oci-DeleteVolume.py [parent compartment] [child compartment] [volume name] [region] [optional argumant]\n" +
        "Use case example deletes the volume from the specified child compartment:\n" +
        "\tOci-DeleteVolume.py admin_comp dbs_comp kentrmanp01_datavol_0 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Usage Error")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
volume_name                     = sys.argv[3]
region                          = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
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
storage_composite_client            = BlockstorageClientCompositeOperations(storage_client)
compute_client                      = ComputeClient(config)
compute_composite_client            = ComputeClientCompositeOperations(compute_client)

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

# check to see if the volume does not exists and if so, raise exception
volumes = GetVolumes(
    storage_client,
    availability_domains,
    child_compartment.id
)
volumes.populate_block_volumes()
volume = volumes.return_block_volume_by_name(volume_name)
error_trap_resource_not_found(
    volume,
    "Volume " + volume_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# proceed with the logic
if len(sys.argv) == 5:
    warning_beep(6)
    print("Enter YES to proceed with deletion of volume {} from compartment {} or any other key to abort: \n".format(
        volume_name,
        child_compartment_name
    ))
    if "YES" != input():
        print("Deletion of volume aborted at user request.\n\n")
        exit(0)
elif option != "--FORCE":
    warning_beep(1)
    print("\n\nINVALID OPTION! The only valid option is --force\nPlease try again with the correct option.\n\n")
    raise RuntimeWarning("INVALID OPTION!")

# proceed to delete the volume
print("\n\nDeleting volume {} from compartment {}, please wait......\n".format(
    volume_name,
    child_compartment_name
))
results = delete_volume(
    storage_composite_client,
    volume.id
).data
if results.lifecycle_state != "TERMINATED":
    warning_beep(6)
    print("\n\nUnable to delete volume due to an unknown error. Please inspect the results below.\n\n")
    sleep(5)
    print(results)
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
else:
    print("Volume deletion successful. Please inspect the results below.\n\n")
    header = [
        "COMPARTMENT",
        "VOLUME",
        "AVAILABILITY DOMAIN",
        "LIFECYCLE STATE",
        "REGION"
    ]
    data_rows = [[
        child_compartment_name,
        results.display_name,
        results.availability_domain,
        results.lifecycle_state,
        region
    ]]
    print(tabulate(data_rows, headers = header, tablefmt = "simple"))