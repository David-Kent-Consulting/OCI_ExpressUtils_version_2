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

# Required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.database import GetDbNode
from lib.database import GetDbSystem

# Required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.database import DatabaseClient
from oci.core import VirtualNetworkClient

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetDbSystem.py : Usage\n\n" +
        "Oci-GetDbSystem.py [parent compartment] [child compartment] [db system name] [region] [optional argument]\n" +
        "Use case example 1 prints all DB systems by name within the specified compartment:\n" +
        "\tOci-GetDbSystem.py admin_comp dbs_comp list_all_db_systems 'us-ashburn-1' --name\n" +
        "Use case example 2 prints the specified DB system details:\n" +
        "\tOci-GetDbSystem.py admin_comp dbs_comp KENTFINCDB 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("INCORRECT USAGE")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
db_system_name                      = sys.argv[3]
region                              = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None # required for logic to work
if option != "--JSON":
    copywrite()
    sleep(2)

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
database_client = DatabaseClient(config)
network_client = VirtualNetworkClient(config)

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

# get DB system data
db_systems = GetDbSystem(
    database_client,
    child_compartment.id
)
db_systems.populate_db_systems()


# run through the logic
if len(sys.argv) == 5 and db_system_name.upper() == "LIST_ALL_DB_SYSTEMS":
    # print(db_systems.return_all_db_systems())
    header = [
        "COMPARTMENT",
        "DATABASE\nCDB",
        "LISTENER",
        "EDITION",
        "STORAGE\nTYPE",
        "STORAGE\nSIZE",
        "SERVICE\nNODE",
        "AVAILABILITY\nDOMAIN",
        "SHAPE",
        "LIFECYCLE\nSTATE",
        "POWER\nSTATE"
    ]
    data_rows = []
    if db_systems.return_all_db_systems() is not None:
        for dbs in db_systems.return_all_db_systems():

            db_nodes = GetDbNode(
            database_client,
            child_compartment.id,
            dbs.id
            )

            db_nodes.populate_db_service_nodes()
            db_node = db_nodes.return_db_service_node_display_name(dbs.hostname)

            data_row = [
                child_compartment_name,
                dbs.display_name,
                dbs.listener_port,
                dbs.database_edition,
                dbs.db_system_options.storage_management,
                dbs.data_storage_size_in_gbs,
                dbs.hostname,
                dbs.availability_domain,
                dbs.shape,
                dbs.lifecycle_state,
                db_node.lifecycle_state
            ]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    print("\n\n")
    db_system = db_systems.return_db_system_from_display_name(db_system_name)
    error_trap_resource_not_found(
        db_system,
        "Database system " + db_system_name + " not found within compartment " + child_compartment_name + " within region " + region
    )
    # no easy way to get the IP addresses bound to the DB System, we have to first get the DB nodes
    # For --node-details we will show all VNIC data, for the DB system, only the node names will be printed
    db_nodes = GetDbNode(
        database_client,
        child_compartment.id,
        db_system.id
    )
    db_nodes.populate_db_service_nodes()
    db_node = db_nodes.return_db_service_node_display_name(db_system.hostname)

    if len(sys.argv) == 5:
        print(db_system)
        print("Service Node:\t\t{}".format(db_node.hostname))
        print("Lifecycle State:\t{}".format(db_node.lifecycle_state))

    elif option == "--OCID":
        print(db_system.id)
    elif option == "--NAME":
        print(db_system.display_name)
    elif option == "--AVAILABILITY-DOMAIN":
        print(db_system.availability_domain)
    elif option == "--STORAGE":
        print("Data storage size in Gbytes       : " + str(db_system.data_storage_percentage))
        print("Data storage allocation in Gbytes : " + str(db_system.data_storage_size_in_gbs))
    elif option == "--DATABASE-EDITION":
        print(db_system.database_edition)
    elif option == "--STORAGE-TYPE":
        print(db_system.db_system_options.storage_management)
    elif option == "--DISK-REDUNDANCY":
        print(db_system.disk_redundancy)
    elif option == "--SERVICE-NODE-NAME":
        print(db_system.hostname)
    elif option == "--LICENSE-MODEL":
        print(db_system.license_model)
    elif option == "--LIFECYCLE-STATE":
        print(db_system.lifecycle_state)
    elif option == "--LISTENER-PORT":
        print(db_system.listener_port)
    elif option == "--NODE-COUNT":
        print(db_system.node_count)
    elif option == "--NODE-DETAILS":
        
        print(db_node)
        vnic = network_client.get_vnic(vnic_id = db_node.vnic_id).data
        print(vnic)

    elif option == "--SHAPE":
        print(db_system.shape)
    elif option == "--JSON":
        print(db_system)
    else:
        print(
            "\n\nINVALID OPTION! Valid options are:\n" +
            "\t--ocid\t\t\tPrints the OCID of the DB System\n" +
            "\t--name\t\t\tPrints the name of the DB System\n" +
            "\t--availability-domain\tPrints the availability domain where the DB System resides\n" +
            "\t--storage\t\tPrints the DB System's storage configuration\n" +
            "\t--database-edition\tPrints the deployed database edition on the DB System\n" +
            "\t--storage-type\t\tPrints the storage type, LVM for logical volume, ASM for Grid Control\n" +
            "\t--disk-redundancy\tPrints the level of disk redundancy\n" +
            "\t--service-node-name\tPrints the name of the service node(s) prividing compute for the DB system\n" +
            "\t--license-model\t\tPrints the license model (included or BYOL) deployed to the DB System\n" +
            "\t--lifecycle-state\tPrints the lifecycle state of the DB System\n" +
            "\t--listener-port\t\tPrints the port the database is listening on\n" +
            "\t--node-count\t\tPrints the number of nodes running the DB System\n" +
            "\t--node-details\t\tPrints the details regarding service nodes for this DB System\n" +
            "\t--shape\t\t\tPrints the compute shape of the DB System\n" +
            "\t--json\t\t\tPrints in JSON format and surpresses other output\n\n" +
            "Please try again with a correct option.\n\n"
        )
        raise RuntimeWarning("INVALID OPTION!")

print("\n\n")