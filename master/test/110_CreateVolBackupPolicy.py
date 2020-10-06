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

if len(sys.argv) != 3: # ARGS PLUS COMMAND
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')


compartment_id      = sys.argv[1]
policy_name         = sys.argv[2]



# functions
def CreateBackupPolicy(block_storage_client, myCompartment_id, myPolicyName):
    backup_policy_details = oci.core.models.CreateVolumeBackupPolicyDetails(
        compartment_id = myCompartment_id,
        display_name = myPolicyName
    )
    results = block_storage_client.create_volume_backup_policy(
        backup_policy_details
    ).data
    print(results)
# end function CreateBackupPolicy

# Default config file and profile
config = oci.config.from_file()

block_storage_client = oci.core.BlockstorageClient(config)


CreateBackupPolicy(block_storage_client, compartment_id, policy_name)
