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

# Required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import return_availability_domain
from lib.general import get_regions
from lib.general import is_int
from lib.general import read_pub_ssh_keys_from_dir
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.database import GetDbNode
from lib.database import GetDbSystem
from lib.database import terminate_db_system

# Required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.database import DatabaseClient
from oci.database import DatabaseClientCompositeOperations

# required OCI decorators
from oci.database.models import UpdateDbSystemDetails

copywrite()
sleep(2)
if len(sys.argv) != 5:
    print(
        "\n\nOci-DeleteDbSystem.py : Usage\n\n" +
        "Oci-DeleteDbSystem.py [parent compartment] [child compartment] [DB system name][region]\n" +
        "Use case example terminates the specified DB System:\n" +
        "\tOci-DeleteDbSystem.py admin_comp dbs_comp KENTBNRCDB 'us-ashburn-1'\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
db_system_name                      = sys.argv[3]
region                              = sys.argv[4]

# instiate the environment and validate that the specified region exists
print("\n\nFetching and verifying tenant resource data. Please wait......\n")
config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config)
regions = get_regions(identity_client)
correct_region = False
for rg in regions:
    if rg.name == region:
        correct_region = True
if not correct_region:
    warning_beep(1)
    print("\n\nWARNING! - Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
database_client = DatabaseClient(config)
database_composite_client = DatabaseClientCompositeOperations(database_client)

# get parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Unable to find parent compartment " + parent_compartment_name + " within tenancy " + config["tenancy"]
)

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Unable to find child compartment " + child_compartment_name + " in parent compartment " + parent_compartment_name
)

# get DB system data and return error if the DB System is found
db_systems = GetDbSystem(
    database_client,
    child_compartment.id
)
db_systems.populate_db_systems()
db_system = db_systems.return_db_system_from_display_name(db_system_name)

error_trap_resource_not_found(
    db_system,
    "Database system " + db_system_name + " not found within compartment " + child_compartment_name + " within region " + region
)

# We must check the DB nodes to ensure they are powered up prior to going onto the next task
db_nodes = GetDbNode(
    database_client,
    child_compartment.id,
    db_system.id
)
db_nodes.populate_db_service_nodes()
for dbn in db_nodes.return_all_db_service_nodes():
    if dbn.lifecycle_state != "TERMINATED" and dbn.lifecycle_state != "TERMINATING":
        if dbn.lifecycle_state != "STOPPED":
            warning_beep(1)
            print("\n\nWARNING! Service node {} is currently in a state of {}\n".format(
                dbn.hostname,
                dbn.lifecycle_state
            ))
            print("DB System {} deletion request requires that all nodes be in an STOPPED state prior to deleting the DB System.\n\n".format(
                db_system_name
            ))
            raise RuntimeWarning("DB System Note Running")


# all pre-reqs are good, prompt user with final message prior to applying the shape change

warning_beep(6)
print("\n\nThis program will delete the DB sytem {} from child compartment {} within region {}\n".format(
    db_system_name,
    child_compartment_name,
    region
))
print("There is no recovery from this operation once started.\n\n")
warning_beep(6)
print("Press any key to continue to the next prompt.")
input()
warning_beep(6)
print("Delete request for DB System {} in compartment {} in region {}\n\n".format(
    db_system_name,
    child_compartment_name,
    region
))
print(
    "You are about to destroy and delete this DB System. Make sure you have good backups if required and\n" +
    "that you are certain this is something that is is an approved action.\n\n"
    "Enter PROCEED_TO_DELETE_DB_INSTANCE and press enter to confirm, or just press the enter key to abort."
)

if "PROCEED_TO_DELETE_DB_INSTANCE" != input():
    print("shape change aborted per user request.\n\n")
else:
    print("\n\nDeleting of DB System {} has been started and cannot be reversed, please wait......\n".format(
        db_system_name
    ))
    delete_db_system_response = terminate_db_system(
        database_composite_client,
        db_system.id
    )

    print("The DB System {} has been deleted from compartment {} within region {}.\n".format(
        db_system_name,
        child_compartment_name,
        region
    ))
    sleep(5)
    print(delete_db_system_response.data)

