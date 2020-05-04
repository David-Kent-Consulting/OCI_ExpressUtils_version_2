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

#if len(sys.argv) != 17: # ARGS PLUS COMMAND
#    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')

compartment_id              = "ocid1.compartment.oc1..aaaaaaaaysl6m26pkjmwh4lpbx6y2bwdlpf6amfv2x5lrtkdcpiae66jfqbq"
'''
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

def GetDbSystem(database_client, compartment_id, myDbSystemName):
    '''
    Returns the DB System that is a member of the compartment
    '''
    db_systems_list = database_client.list_db_systems(compartment_id).data
    for dbs in db_systems_list:
        if dbs.display_name == myDbSystemName and dbs.lifecycle_state != "TERMINATED":
            return dbs

# Default config file and profile
config = oci.config.from_file()
database_client = oci.database.DatabaseClient(config)
database_composite_ops = oci.database.DatabaseClientCompositeOperations(database_client)
virtual_network_client = oci.core.VirtualNetworkClient(config)


try:
    
    
    dbs = GetDbSystem(database_client, compartment_id, "DWTCDB")
    print(dbs)
    update_dbs_details = oci.database.models.UpdateDbSystemDetails(
        shape = dbs.shape
    )
    print (update_dbs_details)


    

finally:
    print("fill this in later")
