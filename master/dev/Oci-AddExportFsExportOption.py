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
from lib.general import GetInputOptions
from lib.general import get_availability_domains
from lib.general import get_regions
from lib.general import is_int
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.filesystems import add_export_option
from lib.filesystems import GetExport
from lib.filesystems import GetMountTarget

from oci.config import from_file
from oci.identity import IdentityClient
from oci.file_storage import FileStorageClient

from oci.file_storage.models import ClientOptions
from oci.file_storage.models import UpdateExportDetails

if len(sys.argv) < 7:
    print(
        "\n\nOci-AddExportFsExportOption.py : Usage\n\n" +
        "Oci-AddExportFsExportOption.py [parent compartment] [child_compartment] [mount target] \\\n" +
        "[purge_with_addition (true/false) [region] [--source] [source CIDR] \\\n" +
        "[additional argument option(s)] [value].....\n\n" +
        "Use case example adds the specified source access permission to the export with root and\n" +
        "read only access to the NFS share:\n" +
        "\tOci-AddExportFsExportOption.py admin_comp dbs_comp KENTFST01_MT true 'us-ashburn-1' \\\n" +
        "\t   --source '172.16.0.5' --access read_only --identity-squash root\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR")

# This program uses the class GetInputOptions to instiate variables from the argument vector.
# Coders should be well versed in this class prior to making changes to this code.
argument_list = GetInputOptions(
    sys.argv
)

# the class method tests that each argument option contains a value
if not argument_list.populate_input_options(6):
    warning_beep(1)
    raise RuntimeError("SYNTAX ERROR! Invalid number of arguments provided by user")

# these are the args that are always expected and required to add export options
parent_compartment_name         = argument_list.argument_list[1]
child_compartment_name          = argument_list.argument_list[2]
mount_target_name               = argument_list.argument_list[3]
region                          = argument_list.argument_list[5]

# purge_with_addition must be True or False, set accordingly
if sys.argv[4].upper() == "TRUE":
    purge_with_addition = True
elif sys.argv[4].upper() == "FALSE":
    purge_with_addition = False
else:
    raise RuntimeWarning("INVALID INPUT! - purge_with_addition must be TRUE or FALSE")

# instiate the options values except for source to None since they are optional. source is required.
require_privileged_source_port = None
access = None
identity_squash = None
anonymous_uid = None
anonymous_gid = None

# get the source input using the class
source = argument_list.return_input_option_data("--source")

#######################################################################################################
# check each expected option and set its value if a value is returned,                                #
# then make sure the values are allowed, raise warning if not                                         #
#######################################################################################################

output_in_json = False
output_in_json = argument_list.return_input_option_data("--output-in-json")
if output_in_json is not None:
    if output_in_json.upper() == "TRUE":
        output_in_json = True

# must be set to false or the default for the export option will be true, which could yield undesirable results
require_privileged_source_port = False
if argument_list.return_input_option_data("--require-privileged-source-port"):
    require_privileged_source_port = argument_list.return_input_option_data("--require-privileged-source-port")
    if require_privileged_source_port.upper() == "TRUE":
        require_privileged_source_port = True
else:
    # all other values are set only when the above value is not true
    if argument_list.return_input_option_data("--access"):
        access = argument_list.return_input_option_data("--access").upper()
        if access not in ["READ_WRITE", "READ_ONLY"]:
            raise RuntimeWarning("INVALID OPTION VALUE! - Value for --access must be READ_WRITE or READ_ONLY") 
    if argument_list.return_input_option_data("--identity-squash"):
        identity_squash = argument_list.return_input_option_data("--identity-squash").upper()
        if identity_squash not in ["ALL", "NONE", "ROOT"]:
            raise RuntimeWarning("INVALID OPTION VALUE! - Value for --identity-squash may only be ALL, NONE, or ROOT") 
    if argument_list.return_input_option_data("--anonymous-uid"):
        anonymous_uid = argument_list.return_input_option_data("--anonymous-uid")
        if not is_int(anonymous_uid):
            raise RuntimeWarning("INVALID OPTION VALUE! - Value for --anonymous-uid must be a number")
        elif int(anonymous_uid) < 1 or int(anonymous_uid) > 65534:
            raise RuntimeWarning("INVALID OPTION VALUE! - Value for --anonymous-uid must be between 1 and 65534") 
        else:
            anonymous_uid = int(anonymous_uid)
    if argument_list.return_input_option_data("--anonymous-gid"):
        anonymous_gid = argument_list.return_input_option_data("--anonymous-gid")
        if not is_int(anonymous_gid):
            raise RuntimeWarning("INVALID OPTION VALUE! - Value for --anonymous-gid must be a number")
        elif int(anonymous_gid) < 1 or int(anonymous_gid) > 65534:
            raise RuntimeWarning("INVALID OPTION VALUE! - Value for --anonymous-gid must be between 1 and 65534") 
        else:
            anonymous_gid = int(anonymous_gid)



#######################################################################################################
# end checking and instiating values other than source                                                #
#######################################################################################################

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

if not output_in_json:
    print("\n\nFetching and validating tenancy resources......\n")
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

# run through the logic to apply the export option set to export_options of the export resource,
# and error handling

update_export_response = add_export_option(
    filesystem_client,
    UpdateExportDetails,
    ClientOptions,
    export,
    source,
    require_privileged_source_port,
    access,
    identity_squash,
    anonymous_uid,
    anonymous_gid,
    purge_with_addition
)


if update_export_response is None:
    warning_beep(1)
    print(
        "\n\nWARNING! Export options addition request could not be applied. The\n" +
        "most common cause of this error is attempting to add a source CIDR\n" +
        "that is already in use. Please validate your input against the\n" +
        "current export options entries within the export and try again.\n\n"
    )
    raise RuntimeWarning("WARNING! DUPLICATE SOURCE ADDRESS")

elif output_in_json:
    print(update_export_response)

else:
    print("\n\nExport option has been applied for source {} to the mount target {}\n".format(
        source,
        mount_target_name
    ))
    print("Please note the current export options list below.\n")
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

