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
import datetime
import subprocess
import json
import oci
import os
import string
import sys

if len(sys.argv) != 4:
    raise RuntimeError('Invalid number of arguments provided to the script. Consult the script header for required arguments')

VM_ID                       = sys.argv[1]
VM_REGION                   = sys.argv[2]
VM_STATE                    = sys.argv[3]



#print(DB_NODE_ID+"\n")
#print(DB_STATE+"\n")
#exit(0)

# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
os.environ["OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNIN"] = "TRUE"
os.environ["SUPPRESS_PYTHON2_WARNING"] = "TRUE"

# Default config file and profile
config = oci.config.from_file()
compute_client = oci.core.ComputeClient(config)
virtual_network_client = oci.core.VirtualNetworkClient(config)

def ChangeVmState(my_VM_ID, my_VM_STATE):
    if str.upper(my_VM_STATE) == 'START':
        print("\nAttempting to start the VM......")
        cmd = 'oci compute instance action --action START --region '+VM_REGION+' --instance-id '+my_VM_ID
        sp  = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=None)
        output, _ = sp.communicate()
        results   = output.decode("utf-8")
        print(results)
    elif str.upper(my_VM_STATE) == 'STOP':
        print("\nAttempting to stop the VM......")
        cmd = 'oci compute instance action --action STOP --region '+VM_REGION+' --instance-id '+my_VM_ID
        sp  = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=None)
        output, _ = sp.communicate()
        results   = output.decode("utf-8")
        print(results)
    else:
        print("\nInvalid option. Valid options are either START or STOP. Please try again.")
        exit (1)

try:
    ChangeVmState(VM_ID, VM_STATE)

    print('\nOperation Complete')
    print('===========================')

finally:
    
    print("\n\nThe job request for changing for the virtual machine state has been completed.\n")
    print("\nPlease inspect the returned messages to determine success or failure.\n")