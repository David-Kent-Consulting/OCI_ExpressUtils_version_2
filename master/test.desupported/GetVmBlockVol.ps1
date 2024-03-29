param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName,
  [parameter(Mandatory=$true)]
    [String]$VmName,
  [parameter(Mandatory=$true)]
    [string]$Region,
  [parameter(Mandatory=$false)]
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

# Functions 
# For an unknown reason, $myVMs.data.count returns 22 when a single array element is present, but returns
# 1 when tested against a var from the calling module. For this reason we depend on $VMs and $VmName
# having been declared by the parent module . Do not run function in a library module.
Function GetVM
{
    $count      = $VMs.data.count
    $count
    $cntr       = 0
#    if ( $count -eq 1 ) { return($myVMs) }
    while ( $cntr -lt $count) {
        if ( $VMs.data[$cntr].'display-name' -eq $VmName -and $VMs.data[$cntr].'lifecycle-state' -ne "TERMINATED" ) {
            return($VMs.data[$cntr])
        }
        $cntr   = $cntr+1
    }
} # end function GetVM

# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

if (!$options){
  Write-Output " "
  Write-Output " "
  Write-Output "Option required to return value:"
  Write-Output "ALL - returns all resource data"
  Write-Output "BLOCKVOLID - OCID for the block volume attached to this host"
  Write-Output "COMPARTMENT - Returns compartment ID where resource resides"
  Write-Output "OCID - Returns OCID of resource"
  Write-Output " "
  Write-Output " "
  return 1
}

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

$myCompartment      = GetActiveChildCompartment $TenantObjects $CompartmentName
if (!$myCompartment) {
  Write-Output "Compartment $CompartmentName not found. Please try again."
  return 1}

$VMs            = GetVMs $myCompartment $Region
if (!$VMs) {
  Write-Output "No VMs found in compartment $CompartmentName. Please try again."
  return 1}

$myVM           = GetVM $VMs $VmName
if (!$myVM) {
  Write-Output "VM Name $VmName not found in compartment $CompartmentName. Please try again."
  return 1}

$myBlockVolumes  = GetBlockVolumes $myVM $Region
if (!$myBlockVolumes) {
  Write-Output "No block volumes associated with Vm $VmName in compartment $CompartmentName. Please try again."
  return 1}

$return         = SelectBlockVolume $myVM $myBlockVolumes

if (!$return){
  Write-Output "No block volumes associated with Vm $VmName in compartment $CompartmentName. Please try again."
  return 1
} else {
  ReturnValWithOptions "GetVmBlockVol.ps1" $return $options
}





