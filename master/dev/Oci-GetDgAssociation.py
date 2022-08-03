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
7. Get the database dataguard association(s)
8. Print the results

'''

# required system modules
import imp
from logging import warning
# import os.path
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

copywrite()

if len(sys.argv) != 7:
    print(
        "\n\nOci-GetDgAssociation.py : Usage\n\n" +
        "Oci-GetDgAssociations.py [parent compartment] [child compartment] [db system name] [db name] [region] [dg region]\n" +
        "Use case example prints all Dataguard associations for this DB system:\n\n" +
        "\tOci-GetDgAssociations.py admin_comp dbs_comp KENTCDB KENTDB 'us-ashburn-1' 'us-phoenix-1\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("INCORRECT USAGE\n\n")


parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
db_system_name                      = sys.argv[3]
db_name                             = sys.argv[4]
region                              = sys.argv[5]
dg_region                           = sys.argv[6]


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

correct_region = False
for rg in regions:
    if rg.name == dg_region:
        correct_region = True
        config["region"] = rg.name
        dg_identity_client = IdentityClient(config)
        dg_database_client = DatabaseClient(config)

if not correct_region:
    print("\n\nWARNING! - Dataguard region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        dg_region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

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

'''
7. Get the database dataguard association(s)

This logic checks for all dataguard (DG) associations per database within the specified region pairs.
It will not check for DG associations in other regions, even though this may be a possibility. There
may also be more than 1 DG association within the same region. We recommend this in teterary configurations.
If checking DG associations between regions, specify the primary and DFR regions in the CLI argv list. For
teterary configurations, supply the primary region name for both arguments.
'''
dg_associations = []

for db in databases:

    count = 0 # used to see if DG associations are found

    dgs_associated_with_db = GetDgAssociations(
        database_client,
        db.id
    )

    dgs_associated_with_db.populate_dg_associations()
    if dgs_associated_with_db.return_all_dg_associations() is None:
        
        print("There are no dataguard associations present for {} in compartment {} within region {}\n\n".format(
            db_system_name,
            child_compartment_name,
            region
        ))
        exit(0)
    
    elif len(dgs_associated_with_db.return_all_dg_associations()) > 0:

        count = count + 1

        data_rows = []

        for dg in dgs_associated_with_db.return_all_dg_associations():

            dg_db_systems = GetDbSystem(
                dg_database_client,
                child_compartment.id
            )
            dg_db_systems.populate_db_systems()
            for dg_db_system in dg_db_systems.return_all_db_systems():
                if dg.peer_db_system_id == dg_db_system.id:
                    print(dg)
                    data_row = [
                        child_compartment.name,#
                        db.db_name,#
                        db_system.display_name,#
                        db_system.hostname,
                        db_system.lifecycle_state,
                        db_system.availability_domain,
                        dg_db_system.display_name,
                        dg_db_system.hostname,
                        dg_db_system.lifecycle_state,
                        dg_db_system.availability_domain,
                        dg.lifecycle_state,
                        dg.role,
                        dg.peer_role,
                        dg.lifecycle_state,
                        dg.transport_type,
                        dg.protection_mode,
                        dg.apply_lag,
                        dg.apply_rate,
                        dg.id

                    ]

                    data_rows.append(data_row)

# 8. Print the results
if len(data_rows) == 0 and count > 0:
    warning_beep(1)
    print("There are no dataguard associations for DB system {} in compartment {} for region {}\n".format(
        db_system_name,
        child_compartment_name,
        dg_region
    ))
    print("Note however that there is at least 1 dataguard association with a database for\n" +
          "this primary DB system.\n")
    print("Please make sure you have specified the correct DB system and respective regions\n" +
          "for both the parent and peered DB systems.\n\n")
elif count == 0:
    pass
else:
    header = [
        "Compartment\nName",
        "Database Name",
        "Parent\nCDB Name",
        "Parent\nService\nNode\nName",
        "Parent\nLifecycle\nState",
        "Parent\nAvailability\nDomain",
        "Peer\nCDB Name",
        "Peer\nServce\nNode\nName",
        "Peer\nLifecycle\nState",
        "Peer\nAvailability\nDomain",
        "Data\nGuard\nLifecycle\nState",
        "Parent\nRole",
        "Peer\nRole",
        "Data\nGuard\nLifecycle\nState",
        "Transport\nType",
        "Protection\nMode",
        "Transaction\nApplication\nLag Time",
        "Transaction\nApplication\nRate",
        "Dataguard\nOCID"
    ]

    print(tabulate(data_rows, headers = header, tablefmt="simple"))

