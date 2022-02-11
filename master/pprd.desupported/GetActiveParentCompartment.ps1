param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName
)


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

Class BackupPolicies
{
    [string]$VolBackPolName
    [array]$VolBackPolSched
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

# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

# functions

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA

$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
if (!$TenantObjects.TenantId.data) { return 1}

$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
if (!$TenantObjects.AllParentCompartments.data) { return 1 }

$return=(GetActiveParentCompartment $TenantObjects $CompartmentName)
if (!$return) { return 1 } else { return($return.id) }

