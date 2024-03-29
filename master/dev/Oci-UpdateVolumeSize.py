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
from lib.general import is_int
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.volumes import GetVolumes
from lib.volumes import increase_volume_size

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import BlockstorageClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import BlockstorageClientCompositeOperations

# required OCI decorators
from oci.core.models import UpdateVolumeDetails

copywrite()
sleep(2)
if len(sys.argv) != 6:
    print(
        "\n\nOci-UpdateVolumeSize.py : Usage\n\n" +
        "Oci-UpdateVolumeSize.py [parent compartment] [child compartment] [volume name] [volume size in Gbytes] [region]\n" +
        "Use case example increases the specified volume size to 2Tbytes:\n" +
        "\tOci-UpdateVolumeSize.py admin_comp dbs_comp kentrmanp01_datavol_0 2048 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Usage Error")

if not is_int(sys.argv[4]):
    raise RuntimeWarning("Integer values are required for volume size.")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
volume_name                     = sys.argv[3]
vol_size_in_gb                  = int(sys.argv[4])
region                          = sys.argv[5]

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
    "Volume " + volume_name + " already present in compartment " + child_compartment_name + " within region " + region
)

# the requested size must be greater than the current size but less than 32Tbyte in size.
if vol_size_in_gb <= volume.size_in_gbs:
    print("\n\nWARNING! Volume must be greater than the current volume size of {} Gbyte\n\n".format(
        volume.size_in_gbs
    ))
    raise RuntimeWarning("WARNING! - Volume size request must be greater than current volume size.")
elif vol_size_in_gb > 32768:
    print("\n\nWARNING! Volume size cannot exceed 32768 Gbytes.\n\n")
    raise RuntimeWarning("WARNING - Max volume size is 32 Tbyes")

# proceed to increase the volume size
print("\nAll prerequisite conditions have been met, provisioning volume {} to a size of {} Gbytes.\n".format(
    volume_name,
    vol_size_in_gb
))
print("Please wait......\n")

volume_size_increase_request_results = increase_volume_size(
    storage_composite_client,
    UpdateVolumeDetails,
    volume.id,
    vol_size_in_gb
).data
if volume_size_increase_request_results.lifecycle_state == "AVAILABLE":
    print("THe volume has been successfully increased to a size of {} Gbytes. Please inspect the results below.\n".format(
        vol_size_in_gb
    ))
    
    header = [
        "COMPARTMENT",
        "AVAILABILITY DOMAIN,"
        "VOLUME",
        "OLD SIZE",
        "NEW SIZE",
        "LIFECYCLE STATE",
        "REGION"
    ]
    data_rows = [[
        child_compartment_name,
        volume_size_increase_request_results.availability_domain,
        volume_size_increase_request_results.display_name,
        volume.size_in_gbs,
        volume_size_increase_request_results.size_in_gbs,
        volume_size_increase_request_results.lifecycle_state,
        region
    ]]
    print(tabulate(data_rows, headers = header, tablefmt = "simple"))
    print("\n\n")

    warning_beep(2)
    print("Do not forget to perform operating system tasks to take advantage of this\nincrease in volume storage for your application.\n")
else:
    warning_beep(1)
    print("\n\nWARNING! The volume size could not be increased due to an error. Please inspect the results below.\n")
    sleep(5)
    print(volume_size_increase_request_results.data)
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")


