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
from time import sleep

# Required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import return_availability_domain
from lib.general import get_regions
from lib.general import is_int
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.database import GetDbSystem
from lib.database import GetDbNode
from lib.database import start_stop_db_node

# Required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.database import DatabaseClient
from oci.database import DatabaseClientCompositeOperations

copywrite()
sleep(2)
if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-StopDbSystem.py : Usage\n\n" +
        "Oci-StopDbSystem.py [parent compartment] [child compartment] [DB system name] [region] [optional argument]\n" +
        "Use case example stops the specified DB System within the specified compartment without prompting the user to confirm:\n" +
        "\tOci-StopDbSystem.py admin_comp dbs_comp KENTBNRCDB 'us-ashburn-1' --force\n" +
        "Remove the --force option to be prompted prior to stopping the DB System.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("USAGE ERROR!")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
db_system_name                      = sys.argv[3]
region                              = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None # required for logic to work

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
    "Database system " + db_system_name + " already present within compartment " + child_compartment_name + " within region " + region
)

# we need to fetch the db node that is servicing the DB System. Note this code is designed for single node
# DB systems at this time. A later revision will account for performing a shutdown with clusters.
db_nodes = GetDbNode(
    database_client,
    child_compartment.id,
    db_system.id
)
db_nodes.populate_db_service_nodes()
db_node = db_nodes.return_db_service_from_db_system_id(
    db_system.id
)
if db_node.lifecycle_state != "AVAILABLE":
    warning_beep(1)
    raise RuntimeWarning("WARNING! DB System is not in a AVAILABLE state.")

# run through the logic
if len(sys.argv) == 5:
    warning_beep(6)
    print("Enter YES to proceed to shutdown DB System {} in compartment {} within region {} or any other key to abort.".format(
        db_system_name,
        child_compartment_name,
        region
    ))
    if "YES" != input():
        print("DB System shutdown aborted per user request.\n\n")
        exit(0)
elif option == "--FORCE":
    pass
else:
    warning_beep(1)
    raise RuntimeWarning("INVALID OPTION! Only --force may be used with this utility.")

# Proceed with the shutdown
shutdown_request_results = start_stop_db_node(
    database_composite_client,
    db_node.id,
    "STOP"
)
print("\n\nShutdown of DB system {} within compartment {} in region {} has been submitted.\n".format(
    db_system_name,
    child_compartment_name,
    region
))
print("It will take up to 20 minutes for the shutdown to complete.\n\n")
