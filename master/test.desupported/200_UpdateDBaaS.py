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
import os
import sys


if len(sys.argv) != 4: # ARGS PLUS COMMAND
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')
    

DB_SYSTEM_ID                        = sys.argv[1]
OPTION                              = sys.argv[2]

# Default config file and profile
config = oci.config.from_file()
database_client = oci.database.DatabaseClient(config)
virtual_network_client = oci.core.VirtualNetworkClient(config)


try:
    
    if str.upper(OPTION) == "SHAPE":
        DB_SYSTEM_SHAPE = sys.argv[3]
        update_dbsystem_details = oci.database.models.UpdateDbSystemDetails(
            shape = DB_SYSTEM_SHAPE
        )
    elif str.upper(OPTION) == "SSHKEY":
        ssh_public_key_path = sys.argv[3]
        ssh_keys = []
        files = os.listdir(ssh_public_key_path)
        for f in files:
            file_name = ssh_public_key_path+"/"+f
            print(file_name)
            with open(file_name, mode='r') as mykey:
                ssh_key = mykey.read()
                ssh_keys.append(ssh_key)
            print(ssh_keys)
        update_dbsystem_details = oci.database.models.UpdateDbSystemDetails(
            ssh_public_keys = ssh_keys
        )
    else:
        raise RuntimeError('Invalid arguments provided to the script. Consult the script header for required arguments')
    print(update_dbsystem_details)
    update_dbsystem_results = database_client.update_db_system(
        db_system_id = DB_SYSTEM_ID,
        update_db_system_details = update_dbsystem_details
        )
    print (update_dbsystem_results)



    print('\n\n\nUpdating DB System')
    print('===========================')
    print('{}\n\n'.format(update_dbsystem_results.data))
   # We can wait until the DB system is available. A DB system can take some time to launch (e.g. on the order
   # of magnitude of hours) so we can change the max_interval_seconds and max_wait_seconds to account for this.
   # The wait_until defaults of checking every 30 seconds and waiting for a maximum of 1200 seconds (20 minutes)
   # may not be sufficient.
   #
   # In the below example, we check every 120 seconds (2 minutes) and wait a max of 21600 seconds (6 hours)
    get_db_system_response = oci.wait_until(
        database_client,
        database_client.get_db_system(update_dbsystem_results.data.id),
        'lifecycle_state',
        'AVAILABLE',
        max_interval_seconds=120,
        max_wait_seconds=1200
    )

    print('\nDB System Available')
    print('===========================')
    print('{}\n\n'.format(get_db_system_response.data))
finally:
    print("The job request for updating the virtual machine database has been completed.\n")
    print("Please inspect the returned messages to determine success or failure.\n")