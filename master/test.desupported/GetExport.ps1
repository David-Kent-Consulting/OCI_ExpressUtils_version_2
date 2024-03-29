param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName,
  [parameter(Mandatory=$true)]
    [String]$MountTargetName,
  [parameter(Mandatory=$true)]
    [string]$AvailabilityDomain,
  [parameter(Mandatory=$true)]
    [string]$Region,
  [parameter(Mandatory=$true)]
    [string]$ExportPath,
  [parameter(Mandatory=$true)]
    [string]$options
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

if (!$options){
  Write-Output " "
  Write-Output " "
  Write-Output "Option required to return value:"
  Write-Output "ALL - returns all resource data"
  Write-Output "COMPARTMENT - Returns compartment ID where resource resides"
  Write-Output "OCID - Returns OCID of resource"
  Write-Output " "
  Write-Output " "
  return 1
}


# functions
Function GetExport(
  [array]$myExportSet,
  [string]$myExportPath
){
  $myExportList = oci fs export list `
                  --export-set-id $myExportSet.data.id `
                  --region $Region `
                  | ConvertFrom-Json -AsHashtable
  $count = $myExportList.data.count
  $cntr = 0
  while ( $cntr -le $count ){
    if ( $myExportList.data[$cntr].path -eq $myExportPath -and $myExportList.data[$cntr].'lifecycle-state' -eq 'ACTIVE'){ 
      return $myExportList.data[$cntr]
    }
    $cntr=$cntr+1
  }
} # end function GetExports

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

$myCompartment  = GetActiveChildCompartment $TenantObjects $CompartmentName
if (!$myCompartment) {
  Write-Output "Compartment name $CompartmentName not found. Please try again."
  return 1}

$MountTargets   = GetMountTargets $myCompartment $AvailabilityDomain $Region

$MountTarget    = GetMountTarget $MountTargets $MountTargetName
if (!$MountTarget) {
  Write-Output "Mount Target $MountTargetName not found in compartment $CompartmentName"
  return $false
}

$ExportSetName  = $MountTarget.'display-name'+' - export set'
$ExportSet      = oci fs export-set list `
    --compartment-id $MountTarget.'compartment-id' `
    --availability-domain $MountTarget.'availability-domain' `
    --display-name $ExportSetName `
    | ConvertFrom-Json -AsHashtable

$result         = GetExport $ExportSet $ExportPath

if (!$result){
                Write-Output "Export Path $ExportPath not found. Please try again"
                return $false
              }

switch($options){
  "ALL"         {return($result)}
  "OCID"        {return($result.id)}
  "EXPORT_SET"  {return($result.'export-set-id')}
  Default       {
                  Write-Output "Invalid option, options are [ALL] [OCID] [EXPORT_SET]"
                  return $false
                }
}

