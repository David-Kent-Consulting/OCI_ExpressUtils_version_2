param(
  [parameter(Mandatory=$true)]
    [String]$CompartmentName,
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

# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

# functions

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA

Write-Host " "
Write-Host " "
Write-Host "Backup report for compartment '$CompartmentName' started on $today"
Write-Host " "
Write-Host "Validating connectivity to the OCI RESTFUL API Service......"
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
$today = Get-Date
Write-Host " "
Write-Host "Validation successful."
Write-Host " "
Write-Host "Retrieving backup history for compartment......"
Write-Host " "
$myBootVolBackups = GetVmBootVolBackups $myCompartment $Region
$myCompartmentBlockVolBackups = GetVmBlockVolBackups $myCompartment $Region
#$myCompartmentBlockVolBackups.data
if ( !$myBootVolBackups ) {
    Write-Output "No volume backups found in compartment $CompartmentName"
    Write-Output " "
    return 1 
}
Write-Host "Backup history retrieved."
Write-Host " "
write-host "Checking for machine instances within the compartment......"
Write-Host " "
$myVMs      = GetVMs $myCompartment $Region
if (!$myVms) {
    Write-Output "No VMS found in compartment $CompartmentName"
    Write-Output " "
    return 1 
}
Write-Host "Check for machine instances completed."
Write-Host " "
Write-Host "Running the report......"
Write-Host " "
#$myBootVolBackups = oci bv boot-volume-backup list `
#     --compartment-id $myCompartment.id `
#     --all `
#     | ConvertFrom-Json
#$myBootVolBackups.data

$count = $myVMs.data.count
$cntr = 0
while ($cntr -le $count-1 ){
#    $cntr
#    $myVMs.data[$cntr].id
    $myVM = ./GetVm.ps1 $CompartmentName $myVMs.data[$cntr].'display-name' $Region ALL
    #$myVM
    #$myVM = oci compute instance get --instance-id $myVMs.data[$cntr].id | ConvertFrom-Json
    #$myVM.data.'compartment-id'
    #$myVM.data.'availability-domain'
    $myVmName = $myVM.'display-name'
    $myBootVolAttachment = ./GetVmBootVol.ps1 $CompartmentName $myVM.'display-name' $Region ALL
    #$myBootVolAttachment
    #write-host "here it is "
    # $myBootVolAttachment.data.'boot-volume-id'
    #Write-Host "there it goes"
    $cntr2=0
    Write-Host "Backup report for Virtual Machine '$myVmName' in region $Region"
    Write-Host " "
    Write-Host "STATUS          BACKUP JOB NAME UTC Time                        VM            SIZE IN GB"
    Write-Host "========================================================================================="
    $myBkUpCnt = 0
# there is an error in the logic here, replace $myBootVolAttachment.data.'boot-volume-id' with the OCID string 
# that matches the VM display name in the AD
    while ( $cntr2 -le $myBootVolBackups.data.count ){
        #$myBootVolAttachment.data.'boot-volume-id'
        #$myBootVolBackups.data[$cntr2].'boot-volume-id'
        if ($myBootVolBackups.data[$cntr2].'boot-volume-id' -eq $myBootVolAttachment.'boot-volume-id' ){
            #$myBootVolBackups.data[$cntr2].'display-name'
            Write-Host $myBootVolBackups.data[$cntr2].'lifecycle-state' "  -  " `
            $myBootVolBackups.data[$cntr2].'display-name' "  -  " `
            $myBootVolBackups.data[$cntr2].type "  -  " `
            $myBootVolBackups.data[$cntr2].'unique-size-in-gbs'
            $myBkUpCnt = $myBkUpCnt+1
        }
        $cntr2=$cntr2+1
    }
    if ( $myCompartmentBlockVolBackups ){
        $myBlockVolAttachment = ./GetVmBlockVol.ps1 $CompartmentName $myVM.'display-name' $Region ALL
        #$myBlockVolAttachment
        $cntr3 = 0
        while ( $cntr3 -le $myCompartmentBlockVolBackups.data.count ){
            if ( $myCompartmentBlockVolBackups.data[$cntr3].'volume-id' -eq $myBlockVolAttachment.'volume-id' ){
                Write-Host $myCompartmentBlockVolBackups.data[$cntr3].'lifecycle-state' `
                    $myCompartmentBlockVolBackups.data[$cntr3].'display-name' "_datavol  -  " `
                    $myCompartmentBlockVolBackups.data[$cntr3].type "  -  " `
                    $myCompartmentBlockVolBackups.data[$cntr3].'unique-size-in-gbs'
                $myBkUpCnt = $myBkUpCnt+1
            }
            $cntr3=$cntr3+1
        }
    }
    Write-Host " "
    Write-Host "There are a total of $myBkUpCnt backup images on file for VM $myVmName in region $Region"
    Write-Host " "
    $cntr=$cntr+1
}
$today = Get-Date
Write-Host " "
Write-Host "Backup report for compartment '$CompartmentName' completed as of $today."
Write-Host " "
Write-Host "Program exiting normally."
Write-Host " "
exit(0)
