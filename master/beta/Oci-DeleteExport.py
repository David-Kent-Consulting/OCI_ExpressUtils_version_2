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
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.filesystems import delete_export
from lib.filesystems import GetExport
from lib.filesystems import GetFileSystem
from lib.filesystems import GetMountTarget

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.file_storage import FileStorageClient
from oci.file_storage import FileStorageClientCompositeOperations

# required OCI decorators
from oci.file_storage.models import ClientOptions
from oci.file_storage.models import CreateExportDetails

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-DeleteExport.py : Usage\n\n" +
        "Oci-DeleteExport.py [parent compartment] [child compartment] [file system]\n" +
        "[mount target] [region] [optional argument]\n\n" +
        "Use case example deletes the export from the file system and mount target without prompting the user:\n" +
        "\tOci-DeleteExport.py admin_comp dbs_comp KENTFST01 KENTFST01_MT 'us-ashburn-1' --force\n" +
        "Remove the --force option to be prompted prior to the export deletion.\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
file_system_name                        = sys.argv[3]
mount_target_name                       = sys.argv[4]
region                                  = sys.argv[5]
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
filesystem_client = FileStorageClient(config)
filesystem_composite_client = FileStorageClientCompositeOperations(filesystem_client)

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

# All ADs must be searched by GetFileSystem, so get them
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# Now check to see of the file system exists, if not raise exception
file_systems = GetFileSystem(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
file_systems.populate_file_systems()
file_system = file_systems.return_filesystem(file_system_name)
error_trap_resource_not_found(
    file_system,
    "File system " + file_system_name + " already present in compartment " + child_compartment_name + " within region " + region
)

# Now check to see if the mount target exists, if not raise exception
mount_targets = GetMountTarget(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
mount_targets.populate_mount_targets()
mount_target = mount_targets.return_mount_target(mount_target_name)
error_trap_resource_not_found(
    mount_target,
    "Mount target " + mount_target_name + " not found in compartment " + child_compartment_name + " within region " + region
)

# see if the export exists, if it does raise exception
exports = GetExport(
    filesystem_client,
    child_compartment.id
)
exports.populate_exports()
# We get the export from export_set_id, which has an entity relationship with the mount target resource object
export = exports.return_export(mount_target.export_set_id)
error_trap_resource_not_found(
    export,
    "An export path is not assigned to the mount target " + mount_target_name
)

# run through the logic
if len(sys.argv) != 7:
    warning_beep(6)
    print("\n\nEnter YES to delete the export associated with mount target {} and file system {} , or any other key to abort".format(
        mount_target_name,
        file_system_name
    ))
    if "YES" != input():
        print("Export delete request aborted per user request.\n\n")
        exit(0)
elif option != "--FORCE":
    raise RuntimeWarning("INVALID OPTION! - The only valid option is --force")

# delete the export
print("Deleting export path from mount target {} and file system {}\n".format(
    mount_target_name,
    file_system_name
))
print("Please wait......\n")

export_delete_response = delete_export(
    filesystem_composite_client,
    export.id
)

if export_delete_response is None:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")
else:
    print("Deletion of export from mount target {} and file system {} completed successfully.\n".format(
        mount_target_name,
        file_system_name
    ))
    row_data = [
        child_compartment_name,
        file_system_name,
        mount_target_name,
        export_delete_response.data.id
    ]
    print(tabulate([row_data], headers = ["COMPARTMENT", "FILE SYSTEM NAME", "MOUNT TARGET NAME", "EXPORT ID"], tablefmt = "simple"))

