param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName,
    [parameter(Mandatory=$true)]
    [string]$BackupPolicyName
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
import-module $Path/DkcSolutionsOciLibrary.psm1


# Classes
Class TenantObjects
{  
    [array]$TenantId
    [array]$AllParentCompartments
    [array]$ParentCompartment
    [array]$ChildCompartments
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
function GetBackupPolicy(
    [array]$myCompartment,
    [string]$myBackupPolicyName
){
    $backup_policies = oci bv volume-backup-policy list `
        --compartment-id $myCompartment.id `
        | ConvertFrom-Json #Requires -Assembly 'fully-qualified-name'
    if (! $backup_policies) {return}
        $count = $backup_policies.data.count
    $cntr  = 0
    while ( $cntr -le $count ) {
        if ($backup_policies.data[$cntr].'display-name' -eq $myBackupPolicyName) {return $backup_policies.data[$cntr]}
    }

} # end function GetBackupPolicy

function CreateBackupPolicy(
    [array]$myCompartment,
    [string]$myPolicyName
) {
    $return = oci bv volume-backup-policy create `
        --compartment-id $myCompartment.id `
        --display-name $myPolicyName
    if (! $return) {
        Write-Output "WARNING! Unable to create backup policy $myPolicyName in compartment $myCompartment"
    } else {
        Write-Output ""
        Write-Output "Policy created......"
        Write-Output ""
        return($return)
    }

    
} # end function CreateBackupPolicy

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

$compartment = GetActiveChildCompartment $TenantObjects $CompartmentName

if (! $compartment) { 
    return(1) 
}

$return = GetBackupPolicy $compartment $BackupPolicyName

if ($return){
    Write-Output "Backup policy $BackupPolicyName exists in compartment $CompartmentName."
    Write-Output "Duplicates are not permitted."
    return
} else {
    CreateBackupPolicy $compartment $BackupPolicyName
}
#CreateBackupPolicy $compartment $BackupPolicyName