param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName,
    [String]$VmName,
    [string]$Region
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

Function ListVolumeBackups(
    [array]$myCompartmentBackups,
    [array]$myVmBootVolumes,
    [string]$myVmName,
    [string]$myRegion
)
{
    $count = $myCompartmentBackups.data.Count
    Write-Output " "
    Write-Output " "
    $cntr       = 0
    $myBkUpCnt  = 0
    Write-Host "Backup report for Virtual Machine $myVmName in region $myRegion"
    Write-Host " "
    Write-Host "STATUS          BACKUP JOB NAME UTC Time                        VM            SIZE IN GB"
    Write-Host "========================================================================================="
    while( $cntr -lt $count ){
        if( $myCompartmentBackups.data[$cntr].'boot-volume-id' -eq $myVmBootVol.'boot-volume-id')
        {
            Write-Host $myCompartmentBackups.data[$cntr].'lifecycle-state' "  -  " `
                $myCompartmentBackups.data[$cntr].'display-name' "  -  " `
                $myCompartmentBackups.data[$cntr].type "  -  " `
                $myCompartmentBackups.data[$cntr].'unique-size-in-gbs'
                $myBkUpCnt = $myBkUpCnt+1
        }
        $cntr   = $cntr+1
    }
    Write-Output " "
    Write-Output "Total number of backup images on file are $myBkUpCnt for VM $myVmName in region $myRegion"
    Write-Output " "
} # end function ListVolumeBackups

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

$myCompartment      = GetActiveChildCompartment $TenantObjects $CompartmentName
if (!$myCompartment) { 
    Write-Output "Compartment $CompartmentName not found"
    Write-Output " "
    return 1
}

$myCompartmentBackups = GetVmBootVolBackups $myCompartment
if (!$myCompartmentBackups) {
    Write-Output "No volume backups found in compartment $CompartmentName"
    Write-Output " "
    return 1 
}

$myVMs      = GetVMs $myCompartment
if (!$myVms) {
    Write-Output "No VMS found in compartment $CompartmentName"
    Write-Output " "
    return 1 
}

$myVM               = GetVM $myVMs $VmName
if (!$myVM) {
    Write-Output "VM Name $VmName not found in compartment $CompartmentName"
    Write-Output " "
    return 1 
}

$myCompartmentBootVolumes    = GetBootVolumes $myVM

$myVmBootVol        = SelectBootVolume $myVM $myCompartmentBootVolumes
ListVolumeBackups $myCompartmentBackups $myVmBootVol $VmName $Region