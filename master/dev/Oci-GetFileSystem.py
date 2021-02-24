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
from lib.filesystems import GetFileSystem

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.file_storage import FileStorageClient

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetFileSystem.pr : Usage\n\n" +
        "Oci-GetFileSystem.py [parent compartment] [child compartment] [file system] [region] [optional argument]\n\n" +
        "Use case example 1 prints all file systems by name, availability domain, and state:\n" +
        "\tOci-GetFileSystem.py admin_comp dbs_comp list_all_filesystems 'us-ashburn-1'\n" +
        "Use case exmaple 2 prints detailed data about the specified file system:\n" +
        "\tOci-GetFileSystem.py admin_comp dbs_comp KENTFST01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
file_system_name                        = sys.argv[3]
region                                  = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None # required for logic to work
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
filesystem_client = FileStorageClient(config)

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

# get file system data
file_systems = GetFileSystem(
    filesystem_client,
    availability_domains,
    child_compartment.id
)
file_systems.populate_file_systems()
file_system = file_systems.return_filesystem(file_system_name)

# run through the logic
if sys.argv[3].upper() == "LIST_ALL_FILESYSTEMS":

    data_rows = []
    header = [
        "COMPARTMENT",
        "FILE SYSTEM",
        "LIFECYCLE STATE",
        "REGION"
    ]
    for fs in file_systems.return_all_filesystems():
        data_row = [
            child_compartment_name,
            fs.display_name,
            fs.lifecycle_state,
            region
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

elif len(sys.argv) == 5:
    
    header = [
        "COMPARTMENT",
        "FILE SYSTEM",
        "LIFECYCLE STATE",
        "REGION"
    ]
    data_rows = [[
        child_compartment_name,
        file_system.display_name,
        file_system.lifecycle_state,
        region
    ]]
    print(tabulate(data_rows, headers = header, tablefmt = "simple"))
    print("\nFilesystem ID :\t" + file_system.id + "\n\n")

elif option == "--OCID":
    print(file_system.id)
elif option == "--NAME":
    print(file_system.display_name)
elif option == "--LIFECYCLE-STATE":
    print(file_system.lifecycle_state)
elif option == "--AVAILABILITY-DOMAIN":
    print(file_system.availability_domain)
elif option == "--JSON":
    print(file_system)

else:
        print(
            "\n\nINVALID OPTION! Valid options include:\n\n" +
            "\t--ocid\t\t\tPrints the OCID of the file system\n" +
            "\t--name\t\t\tPrints the name of the file system\n" +
            "\t--availability-domain\tPrints the availability domain the file system was created in\n" +
            "\t--lifecycle-state\tPrints the state of the file system\n" +
            "\t--json\t\t\tPrints all resource data in JSON format and surpresses other output\n\n" +
            "Please try again with a correct option.\n\n"
        )
        raise RuntimeWarning("INVALID OPTION")


