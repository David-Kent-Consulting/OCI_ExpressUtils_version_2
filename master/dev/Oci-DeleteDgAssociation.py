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


1. Verify regions
2. Get parent compartment data
3. Get child compartment data
4. Get parent DB system data
5. Get the DB homes
6. Get the database(s)
7. Validate the DG OCID
8. Delete the database dataguard association by terminating the peer DB system
9. Print the results
'''

# required system modules
import imp
from logging.handlers import SysLogHandler
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required KCS modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.database import GetDbSystem
from lib.database import GetDatabase
from lib.database import GetDgAssociations

# Required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.database import DatabaseClient
from oci.database.models import UpdateDataGuardAssociationDetails


copywrite()

if len(sys.argv) != 7:
    print(
        "\n\nOci-DeleteDgAssociation.py : Usage\n\n" +
        "Oci-DeleteDgAssociation.py [parent compartment] [child compartment] [db system name] [database name]\n" +
        "datagaurd OCID [region]\n\n" +
        "Use case example deletes the dataguard association for the specified DB system and database\n"
        "\tOci-DeleteDgAssociation.py admin_comp dbs_comp KENTCDB KENTDB <DG OCID> 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("INCORRECT USAGE\n\n")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
db_system_name                      = sys.argv[3]
db_name                             = sys.argv[4]
dg_ocid                             = sys.argv[5]
region                              = sys.argv[6]

# instiate the environment and validate that the specified region exists
config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config)

# 1. Verify regions
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
database_client = DatabaseClient(config)
regions         = get_regions(identity_client)

print("Fetching data from OCI, please wait......\n\n")

# 2. Get parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Unable to find parent compartment " + parent_compartment_name + " within tenancy " + config["tenancy"]
)

# 3. Get child compartment data
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

'''
4. Get parent DB system data

We consider the parent DB system to be the first system that had been created in the DataGuard pair, although
that might not always be the case. We recommend a practice that the parent DB system run at the primary region
within the primary availability domain (AD), and that the secondary or teterary DB system run in a) DR region,
b) within the same region but a different AD.

'''
db_systems = GetDbSystem(
    database_client,
    child_compartment.id
)
db_systems.populate_db_systems()
db_system = db_systems.return_db_system_from_display_name(db_system_name)
error_trap_resource_not_found(
    db_system,
    "Unable to find DB system " + db_system_name + " in compartment " + child_compartment_name + " within region " + region
)

'''
5. Get the DB homes

We need to get the database objects, to do that we need to get the database home OCIDs
This might seem at the surface to be unnecessary, but it is since there may be multiple
databases within each db_home.
'''
db_homes = database_client.list_db_homes(
    compartment_id      = child_compartment.id,
    db_system_id        = db_system.id,
    sort_order          = "ASC"
)

'''
6. Get the databases

There may be one or more CDB databases within a virtual machine, Exedata, or bare metal DB system (bare metal deprecated).
The logic must account for this scenario. Our practice is 1 CDB database per virtual machine database. This must be
checked against each DB home. Our practice is to have 1 DB home per CDB on virtual machine database. The list
databases is populated.
'''
databases = []
for db_home in db_homes.data:
    db_list = GetDatabase(
        database_client,
        child_compartment.id,
        db_home.id
    )
    db_list.populate_databases()
    for db in db_list.return_all_databases():
        databases.append(db)

for db in databases:
    if db.db_name != db_name:
        print("Database {} not found in CDB {} in compartment {} within region {}".format(
            db_name,
            db_system_name,
            child_compartment_name,
            region
        ))
        raise RuntimeWarning("\n\nINVALID DATABASE NAME\n\n")
    else:
        db_id = db.id


# 7. Validate the DG OCID
get_data_guard_association_response = database_client.get_data_guard_association(
    database_id = db.id,
    data_guard_association_id = dg_ocid
    )
if dg_ocid != get_data_guard_association_response.data.id:
    print("Dataguard association OCID\n{}\nnot found in DB system {} in compartment {} within region {}".format(
        dg_ocid,
        db_system_name,
        child_compartment_name,
        region
    ))
    raise RuntimeWarning("\n\nINVALID DATAGUARD OCID\n\n")
else:
# 8. 8. Delete the database dataguard association by terminating the peer DB system
    warning_beep(6)
    print(
        "This operation will delete the DataGuard Association (DG)\n" + dg_ocid +
        "\nwithin the DB system " + db_system_name + " within the compartment\n" +
        child_compartment_name + ". This operation will fail unless the database\n" +
        "associated with the primary DB system and CDB is not in an open state. A\n" +
        "failure to make sure the primary database is open and operational may also \n" +
        "result in corruption in the database system view. This may necessitate the\n" +
        "need for a manua cleanup by the DBA. You must also ensure that the primary\n" +
        "database is the actively open database in the DG peering. Please make sure\n" +
        "that these prerequisits have been met before proceeding.\n\n"
    )
    warning_beep(6)
    print("Enter PROCEED_TO_DELETE_DG_ASSOCIATION to proceed, or simply press enter to about.")
    if input().upper() != "PROCEED_TO_DELETE_DG_ASSOCIATION":
        print("\n\nDataguard delete operation terminated by user.\n\n")
    else:
        terminate_db_system_response = database_client.terminate_db_system(
            db_system_id = get_data_guard_association_response.data.peer_db_system_id
        )
        print("Termination request of Dataguard Assoction OCID\n{}\nCompleted for primary CDB {} in compartment {} within region {}\n".format(
            dg_ocid,
            db_system_name,
            child_compartment_name,
            region
        ))
        print(
            "Please inspect the output below for the OCI request number and follow progress using the console or CLI.\n" +
            "It will take 20-45 minutes for the delete request to complete.\n\n"
            )
        print(terminate_db_system_response.headers)
