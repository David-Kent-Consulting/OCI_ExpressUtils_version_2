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

from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.filesystems import GetExport
from lib.filesystems import GetFileSystem
from lib.filesystems import GetMountTarget

from oci.config import from_file
from oci.identity import IdentityClient
from oci.file_storage import FileStorageClient

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetExport.py : Usage\n\n" +
        "Oci-GetExport.py [parent compartment] [child compartment] [mount target]\n" +
        "[region] [optional arguments]\n\n" +
        "Use case example 1 prints information about the specified export and associations with storage:\n" +
        "\tOci-GetExport.py admin_comp dbs_comp KENTFST01_MT 'us-ashburn-1' --summary\n" +
        "Use case example 2 prints detailed information about the specified export:\n" +
        "\tOci-GetExport.py admin_comp dbs_comp KENTFST01_MT 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
mount_target_name                       = sys.argv[3]
region                                  = sys.argv[4]
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
filesystem_client = FileStorageClient(config)

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


# Now fetch the file system data, if not raise exception
file_systems = GetFileSystem(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
file_systems.populate_file_systems()
file_system = file_systems.return_filesystem_using_id(export.file_system_id)
if file_system is None:
    print("\n\nWARNING! No file system association could be found with this export and mount target {}\n".format(
        mount_target_name
    ))
    print("This is an undefined error. Please escalate to your support team.\n\n")
    raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")

# run through the logic
if len(sys.argv) == 5:
    print(export)
elif option == "--EXPORT-OPTIONS":
    header = ["SOURCE", "ACCESS", "IDENTITY SQUASH", "ANONYMOUS_GID", "ANONYMOUS_UID"]
    export_options = []
    for expo in export.export_options:
        export_options.append([expo.source,
                expo.access,
                expo.identity_squash,
                expo.anonymous_gid,
                expo.anonymous_uid])
    print(tabulate(export_options, headers = header, tablefmt = "grid"))
elif option == "--OCID":
    print(export.id)
elif option == "--NAME":
    print(export.display_name)
elif option == "--LIFECYCLE-STATE":
    print(export.lifecycle_state)
elif option == "--PATH":
    print(export.path)
elif option == "--SUMMARY":
    data_row = [
        child_compartment_name,
        file_system.display_name,
        mount_target_name,
        export.path,
        export.lifecycle_state,
        export.id
    ]
    header = ["COMPARTMENT", "FILE SYSTEM", "MOUNT TARGET", "EXPORT PATH", "STATE", "EXPORT ID"]
    print(tabulate([data_row], headers = header, tablefmt = "grid_tables"))
else:
    print(
        "\n\nINVALID OPTION! - Valid options include:\n" +
        "\t--ocid\t\t\tPrints the OCID of the export resource\n" +
        "\t--name\t\t\tPrints the name of the export resource\n" +
        "\t--lifecycle-state\tPrints the state of the export resource\n" +
        "\t--path\t\t\tPrints the export's root path\n" +
        "\t--export-options\tPrints the exportfs details\n" +
        "\t--summary\t\tPrints a summary of the file system, mount target, and export resources\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    



