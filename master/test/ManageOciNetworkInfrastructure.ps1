import-module .\MessiahOciManageFunctions.psm1
import-module .\DkcSolutionsOciLibrary.psm1

Write-Output "This program had been run to create the original tenant for this client. The program should not be run again"
Write-Output "and is programmed to exit upon invocation. It has been left in place for historical purposes."
Write-Output " "
Write-Output "For questions, contact Hank Wojteczko at David Kent Consulting via hankwojteczko@davidkentconsulting.com"
Write-Output "or call (872) 529-5368"
exit

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


# Classes
Class tenant                        # This object class contains all tenant setup information that the user must input
{
    [ValidateNotNullorEmpty()][string]$ClientName
    [ValidateNotNullorEmpty()][string]$ClientShortName                    
    [ValidateNotNullorEmpty()][string]$TenantId
    [ValidateNotNullorEmpty()][string]$ParentCompartmentName
    [ValidateNotNullorEmpty()][string]$AutomationCompartment
    [ValidateNotNullorEmpty()][string]$AutomationVcnCidr
    [ValidateNotNullorEmpty()][string]$BackupCompartmentName
    [ValidateNotNullorEmpty()][string]$BastionCompartmentName
    [ValidateNotNullorEmpty()][string]$BastionRouteTableCsvFle
    [ValidateNotNullorEmpty()][string]$BastionVcnCidr
    [ValidateNotNullorEmpty()][string]$DatabaseCompartmentName
    [ValidateNotNullorEmpty()][string]$DatabaseVcnCidr
    [ValidateNotNullorEmpty()][string]$TestCompartmentName
    [ValidateNotNullorEmpty()][string]$TestVcnCidr
    [ValidateNotNullorEmpty()][string]$VpnCompartmentName           # We will not manage the VPN in code automation
    [ValidateNotNullorEmpty()][string]$WebCompartmentName
    [ValidateNotNullorEmpty()][string]$WebVcnCidr
} # end class tenant

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

$tenant                 = [tenant]@{
                            ClientName              = "Messiah College"
                            ClientShortName         = "messiah"
                            TenantId                = "ocid1.tenancy.oc1..aaaaaaaadr6zwiuddr3etsgyfnldeaxzqfrd7zij33yizbhfk3b5x6uw54sq"
                            ParentCompartmentName   = "MESSIAH"
                            AutomationCompartment   = "automation"
                            AutomationVcnCidr       = "10.40.4.0/24"
                            BackupCompartmentName   = "backup"
                            BastionCompartmentName  = "bastion"
                            BastionVcnCidr          = "10.40.255.0/24"
                            BastionRouteTableCsvFle = "bastionRoutes.csv"
                            DatabaseCompartmentName = "database"
                            DatabaseVcnCidr         = "10.40.0.0/24"
                            TestCompartmentName     = "test"
                            TestVcnCidr             = "10.40.1.0/24"
                            VpnCompartmentName      = "vpn"
                            WebCompartmentName      = "web"
                            WebVcnCidr              = "10.40.2.0/23"                     
} # end define object $tenant

$TenantObjects          = [TenantObjects]@{
                            TenantId                = ''
                            AllParentCompartments   = ''
                            ParentCompartment       = ''
                            ChildCompartments       = ''
} # end define object $TenantObjects

$BackupPolicies         = [BackupPolicies]@{
                            VolBackPolName          = "Banner_BlockVol_Bk_Pol"
                            VolBackPolSched         = ''
}

$ANSIBLE_HOME = "/Users/henrywojteczko/bin"
# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

# functions



# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
Write-Output "Fetching compartment data......"
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
if (!$TenantObjects.TenantId.data) {
    Write-Output " "
    Write-Output " "
    Write-Output "WARNING! Tenant ID $tenant.TenantId not found."
    Write-Output "Please correct and try again."
    Write-Output " "
    return 1
}

Write-Output " "
Write-Output "Fetching the parent container data for the tenant......"
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
if (!$TenantObjects.AllParentCompartments.data) {
    Write-Output " "
    Write-Output " "
    Write-Output "WARNING! An error with OCI has ocurred. Please make note of the preceeding error and contact"
    Write-Output "Oracle support."
    Write-Output " "
    return 1
}

Write-Output " "
Write-Output "Fetching child compartments from the parent compartment...... "
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id
if (!$TenantObjects.ChildCompartments.data) {
    Write-Output " "
    Write-Output " "
    Write-Output "WARNING! Child compartments and/or parent compartment data could not be retrieved."
    Write-Output "Please make sure your data input is correct and try again."
    Write-Output " "
    return 1
}



Write-Output " "
Write-Output "Managing OCI Virtual Cloud Networks......."
Write-Output " "
ManageVcns $tenant $TenantObjects

Write-Output " "
Write-Output "Managing OCI Cloud Subnetworks and other cloud infrastructure. This will take an extended amount of time"
Write-Output "and will send a lot of output to your terminal. Please check the results with care."
Write-Output " "
Write-Output "Starting inspection and management of subnetworks now......"
Write-Output " "
ManageSubnets $tenant $TenantObjects
Write-Output " "
Write-Output "Inspection of subnetworks is complete."

Write-Output " "
Write-Output "Starting inspection of local peering gateways now......"
ManageLPGs
Write-Output " "
Write-Output "Inspection of local peering gateways is complete."
Write-Output " "
Write-Output "Starting inspection of the local peering router tables now......"
ManageLpgRouters $TenantObjects $tenant
Write-Output " "
Write-Output "Inspection of the local peering router tables is now complete."
#ManageBkuPol $tenant $TenantObjects $BackupPolicies

