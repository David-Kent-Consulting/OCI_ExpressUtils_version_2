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


# Set the environment up
$LibPath    = Get-ChildItem -Path env:ANSIBLE_LIB_PATH
$Path=$LibPath.Value
if (!$LibPath){
    Write-Output "ANSIBLE_LIB_PATH environment variable undefined. Please define and set to the path of the"
    Write-Output "DKC Ansible library and try again."
    Write-Output " "
    Write-Output "Hint: export ANSIBLE_LIB_PATH=/home/ansible/prod"
    Write-Output
}
Set-Location $Path
import-module $Path/MessiahOciManageFunctions.psm1
import-module $Path/DkcSolutionsOciLibrary.psm1

# Classes
Class TenantObjects
{  
    [array]$TenantId
    [array]$AllParentCompartments
    [array]$ParentCompartment
    [array]$ChildCompartments
}

# functions
Function CreateDBaaS{
    Start-Process -Path $myPython `
    -ArgumentList $myProg, `
        $DB_COMPARTMENT_OCID, `
        $AVAILABILITY_DOMAIN, `
        $DB_SSH_KEY, `
        $ADMIN_PASSWORD, `
        $DB_CONTAINER_NAME, `
        $DB_DISPLAY_NAME, `
        $DB_NODE_COUNT, `
        $DB_PDB_NAME, `
        $DB_VERSION, `
        $DB_SYSTEM_CPU_CORE_COUNT, `
        $DB_SYSTEM_NAME, `
        $DB_SYSTEM_STORAGE_GB, `
        $DB_SYSTEM_DB_EDITION, `
        $DB_SYSTEM_SHAPE, `
        $DB_SYSTEM_STORAGE_MGMT, `
        $DB_SUBNET_OCID
}

# global vars
# The file tenant.json is critical for these programs to run. We build a dictionary object in hash table form and build
# objects using the OCI CLI SDK to populate $TenantObjects. We also reference back to $tenant throughout this and other
# modules.
$tenant                 = Get-Content -Path $Path/tenant.json | ConvertFrom-Json -AsHashtable
$TenantObjects          = [TenantObjects]@{
                            TenantId                = ''
                            AllParentCompartments   = ''
                            ParentCompartment       = ''
                            ChildCompartments       = ''
} # end define object $TenantObjects
$myPython                   = "/usr/bin/python3"                        # Modify to location of client's python3 virtual env
$myProg                     = $Path+"/200_CreateDBaaS.py"               # This is the python program that creates the DBaaS

# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

################################################################################################################
###                                                         DBaaS MESDBT01                                   ###
################################################################################################################
#$AVAILABILITY_DOMAIN        = "vSHs:US-ASHBURN-AD-1"
#$ADMIN_PASSWORD             = "ADummyPassw0rd_#1"
#$DB_COMPARTMENT_OCID        = "ocid1.compartment.oc1..aaaaaaaaysl6m26pkjmwh4lpbx6y2bwdlpf6amfv2x5lrtkdcpiae66jfqbq"
#$DB_CONTAINER_NAME          = 'TESTCDB'
#$DB_DISPLAY_NAME            = 'TESTCDB'
#$DB_NODE_COUNT              = 1
#$DB_PDB_NAME                = 'TEST'
#$DB_VERSION                 = '12.2.0.1.200114'
#$DB_SSH_KEY                 = "/home/ansible/.ssh/.ssh/id_rsa.pub"
#$DB_SUBNET_OCID             = "ocid1.subnet.oc1.iad.aaaaaaaar4ceiattvjci4x5v7yezscnwgfykkrmriwfgzzpce5w5dr6zva7q"
#$DB_SYSTEM_CPU_CORE_COUNT   = 1
#$DB_SYSTEM_NAME             = 'mesdbt01'
#$DB_SYSTEM_STORAGE_GB       = 512
#$DB_SYSTEM_DB_EDITION       = 'ENTERPRISE_EDITION'
#$DB_SYSTEM_SHAPE            = 'VM.Standard2.1'
#$DB_SYSTEM_STORAGE_MGMT     = 'ASM'

#CreateDBaaS

################################################################################################################
###                                                         DBaaS MESDBT02                                   ###
################################################################################################################
#$AVAILABILITY_DOMAIN        = "vSHs:US-ASHBURN-AD-1"
#$ADMIN_PASSWORD             = "ADummyPassw0rd_#1"
#$DB_COMPARTMENT_OCID        = "ocid1.compartment.oc1..aaaaaaaaysl6m26pkjmwh4lpbx6y2bwdlpf6amfv2x5lrtkdcpiae66jfqbq"
#$DB_CONTAINER_NAME          = 'ODSTCDB'
#$DB_DISPLAY_NAME            = 'ODSTCDB'
#$DB_NODE_COUNT              = 1
#$DB_PDB_NAME                = 'ODSTEST'
#$DB_VERSION                 = '12.2.0.1.200114'
#$DB_SSH_KEY                 = "/home/ansible/.ssh/id_rsa.pub"
#$DB_SUBNET_OCID             = "ocid1.subnet.oc1.iad.aaaaaaaar4ceiattvjci4x5v7yezscnwgfykkrmriwfgzzpce5w5dr6zva7q"
#$DB_SYSTEM_CPU_CORE_COUNT   = 1
#$DB_SYSTEM_NAME             = 'mesdbt02'
#$DB_SYSTEM_STORAGE_GB       = 512
#$DB_SYSTEM_DB_EDITION       = 'ENTERPRISE_EDITION'
#$DB_SYSTEM_SHAPE            = 'VM.Standard2.1'
#$DB_SYSTEM_STORAGE_MGMT     = 'ASM'

#CreateDBaaS

################################################################################################################
###                                                         DBaaS MESDBT03                                   ###
################################################################################################################
$AVAILABILITY_DOMAIN        = "vSHs:US-ASHBURN-AD-1"
$ADMIN_PASSWORD             = "ADummyPassw0rd_#1"
$DB_COMPARTMENT_OCID        = "ocid1.compartment.oc1..aaaaaaaaysl6m26pkjmwh4lpbx6y2bwdlpf6amfv2x5lrtkdcpiae66jfqbq"
$DB_CONTAINER_NAME          = 'DWTCDB'
$DB_DISPLAY_NAME            = 'DWTCDB'
$DB_NODE_COUNT              = 1
$DB_PDB_NAME                = 'DWTEST'
$DB_VERSION                 = '19.6.0.0'
$DB_SSH_KEY                 = "/home/ansible/.ssh/DBaaS_rsa.pub"
$DB_SUBNET_OCID             = "ocid1.subnet.oc1.iad.aaaaaaaar4ceiattvjci4x5v7yezscnwgfykkrmriwfgzzpce5w5dr6zva7q"
$DB_SYSTEM_CPU_CORE_COUNT   = 1
$DB_SYSTEM_NAME             = 'mesdbt03'
$DB_SYSTEM_STORAGE_GB       = 256
$DB_SYSTEM_DB_EDITION       = 'ENTERPRISE_EDITION'
$DB_SYSTEM_SHAPE            = 'VM.Standard2.1'
$DB_SYSTEM_STORAGE_MGMT     = 'LVM'

CreateDBaaS