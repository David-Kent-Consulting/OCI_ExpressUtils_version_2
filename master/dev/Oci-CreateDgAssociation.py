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
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required KCS modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
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

if len(sys.argv) != 12:
    print(
        "\n\nOci-CreateDgAssociation : Usage\n\n"+
        "Oci-CreateDgAssociation.py [parent compartment] [child compartment] [primary DB system] [database name]\n" +
        "[primary DB system region] [DG DB system name] [DG database password] [protection mode] [transport type]\n" +
        "[Active DG Mode Enabled (Y/N)] [DG DB system region]\n" +
        "Use case example enables Dataguard for the DB system and database specified below:\n" +
        "\tOci-CreateDgAssociation.py admin_comp dbs_comp KENTCDB KENTDB 'us-ashburn-1' KENTDRCDB <DB password>\n" +
        "\t\tMAXIMUM_AVAILABILITY ASYNC N 'us-phoenix-1'\n\n"
    )
    raise RuntimeWarning("INVALID USAGE\n\n")

parent_compartment_name                                 = sys.argv[1]
child_compartment_name                                  = sys.argv[2]
db_system_name                                          = sys.argv[3]
db_name                                                 = sys.argv[4]
region                                                  = sys.argv[5]

dg_db_system_details = {
    db_system_name                                      : "",
    database_admin_password                             : "",
    protection_mode                                     : "",
    transport_type                                      : "",
    is_active_data_guard_enabled                        : "",
}
dg_db_system_details["db_system_name"]                  = sys.argv[6]
dg_db_system_details["transport_type"]                  = sys.argv[7]
dg_db_system_details["protection_mode"]                 = sys.argv[8]
dg_db_system_details["transport_type"]                  = sys.argv[9]
dg_db_system_details["is_active_data_guard_enabled"]    = sys.argv[10]

dg_region                                               = sys.argv[11]