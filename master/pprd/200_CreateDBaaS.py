#!/Users/henrywojteczko/bin/python
# Modify the above entry to point to the client's python3 virtual environment prior to execution

'''
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
import oci
import os.path
import sys

if len(sys.argv) != 17: # ARGS PLUS COMMAND
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')

compartment_id              = sys.argv[1]
availability_domain         = sys.argv[2]
ssh_public_key_path         = os.path.expandvars(os.path.expanduser(sys.argv[3]))
ADMIN_PASSWORD              = sys.argv[4]
DB_CONTAINER_NAME           = sys.argv[5]
DB_DISPLAY_NAME             = sys.argv[6]
DB_NODE_COUNT               = int(sys.argv[7])
DB_PDB_NAME                 = sys.argv[8]
DB_VERSION                  = sys.argv[9]
DB_SYSTEM_CPU_CORE_COUNT    = int(sys.argv[10])
DB_SYSTEM_NAME              = sys.argv[11]
DB_SYSTEM_STORAGE_GB        = int(sys.argv[12])
DB_SYSTEM_DB_EDITION        = sys.argv[13]
DB_SYSTEM_SHAPE             = sys.argv[14]
DB_SYSTEM_STORAGE_MGMT      = sys.argv[15]
DB_SUBNET_OCID              = sys.argv[16]
'''
print(compartment_id+"\n")
print(availability_domain+"\n")
print(ssh_public_key_path+"\n")
print(ADMIN_PASSWORD+"\n")
print(DB_CONTAINER_NAME+"\n")
print(DB_DISPLAY_NAME+"\n")
print(str(DB_NODE_COUNT)+"\n")
print(DB_PDB_NAME+"\n")
print(DB_VERSION+"\n")
print(str(DB_SYSTEM_CPU_CORE_COUNT)+"\n")
print(DB_SYSTEM_NAME+"\n")
print(str(DB_SYSTEM_STORAGE_GB)+"\n")
print(DB_SYSTEM_DB_EDITION+"\n")
print(DB_SYSTEM_SHAPE+"\n")
print(DB_SYSTEM_STORAGE_MGMT+"\n")
print(DB_SUBNET_OCID+"\n")
exit(0)
'''

# Default config file and profile
config = oci.config.from_file()
database_client = oci.database.DatabaseClient(config)
virtual_network_client = oci.core.VirtualNetworkClient(config)


try:
    
    with open(ssh_public_key_path, mode='r') as file:
        ssh_key = file.read()

    launch_db_system_details = oci.database.models.LaunchDbSystemDetails(
        availability_domain=availability_domain,
        compartment_id=compartment_id,
        cpu_core_count=DB_SYSTEM_CPU_CORE_COUNT,
        database_edition=DB_SYSTEM_DB_EDITION,
        db_home=oci.database.models.CreateDbHomeDetails(
            db_version=DB_VERSION,
            display_name=DB_DISPLAY_NAME,
            database=oci.database.models.CreateDatabaseDetails(
                admin_password=ADMIN_PASSWORD,
                db_name=DB_PDB_NAME
            )
        ),
        db_system_options = oci.database.models.DbSystemOptions(
            storage_management = DB_SYSTEM_STORAGE_MGMT
        ),
        display_name=DB_DISPLAY_NAME,
        hostname=DB_SYSTEM_NAME,
        initial_data_storage_size_in_gb = DB_SYSTEM_STORAGE_GB,
        shape=DB_SYSTEM_SHAPE,
        ssh_public_keys=[ssh_key],
        subnet_id=DB_SUBNET_OCID,
        node_count = DB_NODE_COUNT
    )

    launch_response = database_client.launch_db_system(launch_db_system_details)
    print('\nLaunched DB System')
    print('===========================')
    print('{}\n\n'.format(launch_response.data))

    # We can wait until the DB system is available. A DB system can take some time to launch (e.g. on the order
    # of magnitude of hours) so we can change the max_interval_seconds and max_wait_seconds to account for this.
    # The wait_until defaults of checking every 30 seconds and waiting for a maximum of 1200 seconds (20 minutes)
    # may not be sufficient.
    #
    # In the below example, we check every 120 seconds (2 minutes) and wait a max of 21600 seconds (6 hours)
    get_db_system_response = oci.wait_until(
        database_client,
        database_client.get_db_system(launch_response.data.id),
        'lifecycle_state',
        'AVAILABLE',
        max_interval_seconds=120,
        max_wait_seconds=21600
    )

    print('\nDB System Available')
    print('===========================')
    print('{}\n\n'.format(get_db_system_response.data))
finally:
    print("The job request for creating the virtual machine database for "+DB_SYSTEM_NAME+ " has been completed.\n")
    print("Please inspect the returned messages to determine success or failure.\n")