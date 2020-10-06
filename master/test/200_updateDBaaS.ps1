param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName,
  [parameter(Mandatory=$true)]
    [String]$DbSystemName,
  [parameter(Mandatory)]
    [string]$option,
  [parameter(Mandatory=$true)]
    [string]$ChangeParameter,
    [parameter(Mandatory=$true)]
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

# shape should contain a list of valid VM shapes for the DBaaS.
# see https://docs.cloud.oracle.com/en-us/iaas/Content/Database/Concepts/overview.htm
# for the most current list of valid shapes.
$shape_list             = `
                            "VM.Standard2.1", `
                            "VM.Standard2.2", `
                            "VM.Standard2.4", `
                            "VM.Standard2.8", `
                            "VM.Standard2.16",
                            "VM.Standard2.24"



# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
Write-Output "Validating the Tenancy......"
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

$myCompartment  = GetActiveChildCompartment $TenantObjects $CompartmentName
Write-Output "Validating the compartment......"
if (!$myCompartment) {
  Write-Output "Compartment name $CompartmentName not found. Please try again."
  return 1}

$myDbSystems = GetDbSystems $myCompartment $DbSystemName $Region
Write-Output "Getting the DB System......"
if ( !$myDbSystems ) { 
  Write-Output "No DB systems found in compartment $CompartmentName. Please try again."
  return 1}



foreach ( $d in $myDbSystems.data ){
    if ( $d.'display-name' -eq $DbSystemName -and $d.'lifecycle-state' -ne 'TERMINATED' ){
        $myDbSystem = $d
    } 
}
if (!$myDbSystem){
    Write-Output "The Database System $DbSystemName could not be found in compartment $CompartmentName."
    Write-Output "Please try again."
    return 1
}
#$myDbSystem
$myDbNode = GetDbNodeName $myDbSystems $myDbSystem.hostname $Region
if ( !$myDbNode ){
    Write-Output "No service nodes found for the DB System $DbSystemName"
    Write-Output "This is an invalid configuration."
    Write-Output "Contact Oracle Support at https://support.oracle.com for immediate help."
    return 1
}
#$myDbNode
Write-Output " "
Write-Output "All prerequisits have been met. Applying change......"
Write-Output " "

if ( $myDbSystem.'lifecycle-state' -ne 'AVAILABLE' ){
    Write-Output "The Database System is not in a correct lifecycle state for any changes."
    $state = $myDbSystem.'lifecycle-state'
    Write-Output "Current state is $state."
    exit 1
} elseif ( $myDbNode.'lifecycle-state' -ne 'AVAILABLE' ) {
    Write-Output "The Database Service Node(s) is not in a correct lifecycle state for any changes."
    $state = $myDbNode.'lifecycle-state'
    Write-Output "Current state is $state."
    exit 1
}

switch ($option) {
    "SSHKEY"    {
        python 200_UpdateDBaaS.py $myDbSystem.id "SSHKEY" $ChangeParameter
        exit(0)
    }
    "SHAPE"     {
        foreach ( $s in $shape_list ) {
            if ( $s -eq $ChangeParameter ) {
                python 200_UpdateDBaaS.py $myDbSystem.id "SHAPE" $ChangeParameter
                exit(0)
            }
        }
        Write-Output "Virtual Machine $ChangeParameter is not valid for the DB System."
        Write-Output "Valid shapes are:"
            foreach ( $s in $shape_list ){
                Write-Output $s
            }
            exit (1)
        
    }
    default     {
        Write-Output "Invalid option. Valid options are 'SSHKEY' or 'SHAPE'"
        Write-Output "Please try again."
        exit (1)
    }
}