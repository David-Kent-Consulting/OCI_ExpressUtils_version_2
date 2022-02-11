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

if len(sys.argv) != 2: # ARGS PLUS COMMAND
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')

config = oci.config.from_file()
block_storage_client    = oci.core.BlockstorageClient(config)
boot_volume_backup_id   = "ocid1.bootvolumebackup.oc1.iad.abuwcljtz2jriz4ikk4sz6ipgzarx2fuyqes6ohsb5jxwzpfbjfchlpnaeia"
destination_region      = str.lower(sys.argv[1])
backup_type             = 'BOOTVOL'

try:
    if backup_type == 'BOOTVOL':
        copy_boot_volume_backup_details = oci.core.models.CopyVolumeBackupDetails (
            destination_region = destination_region
        )
        #print ( copy_boot_volume_backup_details)
        copy_bootvol_backup_results = block_storage_client.copy_boot_volume_backup(
            boot_volume_backup_id = boot_volume_backup_id,
            copy_boot_volume_backup_details = copy_boot_volume_backup_details
        ).data
    print (copy_bootvol_backup_results)
finally:
    print ("All done\n")