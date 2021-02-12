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

# required built-in modules
import os.path
import sys
from time import sleep
# the following must be added to the python library with PIP and the path to anaconda must be appended to PYTHONPATH
# use caution when modifying the PYTHONPATH env var, test everything
from tabulate import tabulate

from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.filesystems import delete_export_option
from lib.filesystems import GetExport
from lib.filesystems import GetMountTarget

from oci.config import from_file
from oci.identity import IdentityClient
from oci.file_storage import FileStorageClient

from oci.file_storage.models import ClientOptions
from oci.file_storage.models import UpdateExportDetails

if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-DeleteExportFsOption.py : Usage\n\n" +
        "Oci-DeleteExportFsOption.py [parent compartment] [child compartment] [mount target]\n" +
        "[source] [region] [optional argument]\n\n" +
        "Use case example deletes the export option from the export within the mount target without prompting the user:\n" +
        "\tOci-DeleteExportFsOption.py admin_comp dbs_comp KENTFST01_MT '172.16.0.57' 'us-ashburn-1' --force\n" +
        "Remove the --force option to be prompted prior to deleting the export option.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
mount_target_name                       = sys.argv[3]
source                                  = sys.argv[4]
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

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
filesystem_client = FileStorageClient(config)

print("\n\nFetching and validating tenancy resource data......")
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

# availability domains is required
availability_domains = get_availability_domains(
    identity_client,
    child_compartment.id
)

# get the mount target resource data
mount_targets = GetMountTarget(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
mount_targets.populate_mount_targets()
mount_target = mount_targets.return_mount_target(mount_target_name)
error_trap_resource_not_found(
    mount_target,
    "Mount target " + mount_target_name + " not found within compartment " + child_compartment_name + " in region " + region
)

# get the export data
exports = GetExport(
    filesystem_client,
    child_compartment.id
)
exports.populate_exports()
export = exports.return_export(mount_target.export_set_id)
error_trap_resource_not_found(
    export,
    "No export found within mount target " + mount_target_name + " in region " + region
)

# check to see if the source targeted for removal exists
source_found = False
for src in export.export_options:
    if src.source == source:
        source_found = True

if not source_found:
    warning_beep(1)
    print("\n\nSource CIDR {} not present within the mount target {} export option entries\n\n".format(
        source,
        mount_target_name
    ))
    raise RuntimeWarning("SOURCE ADDRESS NOT FOUND")

# Run through the logic
if len(sys.argv) == 6:
    warning_beep(6)
    print("Enter YES to delete source {} from the mount target {} export option entries, or any other key to abort".format(
        source,
        mount_target_name
    ))
    if "YES" != input():
        print("Export option delete request aborted per user request\n\n")
        exit(0)
elif option != "--FORCE":
    warning_beep(1)
    raise RuntimeWarning("INVALID OPTION! - The only valid option is --force")

# proceed with deleting the export option
update_export_response = delete_export_option(
    filesystem_client,
    UpdateExportDetails,
    ClientOptions,
    export,
    source
)

if update_export_response is None:
    raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
else:
    print("\n\nExport option for source {} successfully deleted from mount target {} export option entries.\n".format(
        source,
        mount_target_name
    ))
    print("Please review the remaining export options entry below:\n\n")
    
    header = [
        "MOUNT TARGET",
        "EXPORT ROOT PATH",
        "SOURCE ADDRESS",
        "ACCESS",
        "IDENTITY SQUASH",
        "ANONYMOUS UID",
        "ANONYMOUS GID",
        "REQUIRE\nPRIVILEDGED\nSOURCE PORT"
        ]
    data_rows = []

    for expo in update_export_response.export_options:
        data_row = [
            mount_target_name,
            export.path,
            expo.source,
            expo.access,
            expo.identity_squash,
            expo.anonymous_uid,
            expo.anonymous_gid,
            expo.require_privileged_source_port
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

