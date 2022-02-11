# MessiahOciManageFunctions.psm1

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



Function ManageBkuPol(
    [array]$mytenant,
    [array]$myTenantObject,
    [array]$myBackupPolicies)
{
    $compartment            = GetActiveChildCompartment $myTenantObject $mytenant.BackupCompartmentName
    $TenantBackupPolicies   = oci bv volume-backup-policy list --compartment-id $compartment.id
    if (!$TenantBackupPolicies) {
        $TenantBackupPolicies = CreateBackupPolicies $compartment $myBackupPolicies
    }
} # end function ManageBkuPol

Function ManageLpgRouters(
    [array]$myTenantObjects,
    [array]$myTenant
    )
{
    # Check Automation LPG Router
    $myLpgRouter  = $myTenant.AutomationCompartment+"LpgRouteTable"
    $compartment  = GetActiveChildCompartment $myTenantObjects $myTenant.AutomationCompartment
    $myVcn        = GetVcn $compartment | ConvertFrom-Json
    $myLpgRouters = GetRouteTable $myVcn
    Write-Output "Router Table for Automation Compartment must be checked."
    Write-Output "Checking it now......"
    $myLPGs       = GetLPGs $myVcn
    $myLPG        = SelectLPG AutomationToWebLPG $myLPGs
    AnsibleCreateLpgRouter $myLpgRouter $compartment $myVcn $myLPG
    # Check Bastion LPG Router
    $myLpgRouter  = $myTenant.BastionCompartmentName+"LpgRouteTable"
    $compartment  = GetActiveChildCompartment $myTenantObjects $myTenant.BastionCompartmentName
    $myVcn        = GetVcn $compartment | ConvertFrom-Json
    $myLpgRouters = GetRouteTable $myVcn
    Write-Output "Router Table for Bastion Compartment must be checked."
    Write-Output "Checking it now......"
    $myLPGs       = GetLPGs $myVcn
    $myLPG        = SelectLPG BastionToWebLPG $myLPGs
    AnsibleCreateLpgRouter $myLpgRouter $compartment $myVcn $myLPG
    # Check Database LPG Router
    $myLpgRouter  = $myTenant.DatabaseCompartmentName+"LpgRouteTable"
    $compartment  = GetActiveChildCompartment $myTenantObjects $myTenant.DatabaseCompartmentName
    $myVcn        = GetVcn $compartment | ConvertFrom-Json
    $myLpgRouters = GetRouteTable $myVcn
    Write-Output "Router Table for Database Compartment must be checked."
    Write-Output "Checking it now......"
    $myLPGs       = GetLPGs $myVcn
    $myLPG        = SelectLPG DatabaseToWebLPG $myLPGs
    AnsibleCreateLpgRouter $myLpgRouter $compartment $myVcn $myLPG
    # Check Test LPG Router
    $myLpgRouter  = $myTenant.TestCompartmentName+"LpgRouteTable"
    $compartment  = GetActiveChildCompartment $myTenantObjects $myTenant.TestCompartmentName
    $myVcn        = GetVcn $compartment | ConvertFrom-Json
    $myLpgRouters = GetRouteTable $myVcn
    Write-Output "Router Table for Test Compartment must be checked."
    Write-Output "Checking it now......"
    $myLPGs       = GetLPGs $myVcn
    $myLPG        = SelectLPG TestToWebLPG $myLPGs
    AnsibleCreateLpgRouter $myLpgRouter $compartment $myVcn $myLPG
    # Check Web LPG Router
    $myLpgRouter  = $myTenant.WebCompartmentName+"LpgRouteTable"
    $compartment  = GetActiveChildCompartment $myTenantObjects $myTenant.WebCompartmentName
    $myVcn        = GetVcn $compartment | ConvertFrom-Json
    $myLpgRouters = GetRouteTable $myVcn
    Write-Output "Router Table for Web Compartment must be checked."
    Write-Output "Checking it now......"
    $myLPGs       = GetLPGs $myVcn
    $myLPG        = SelectLPG WebToTestLPG $myLPGs
    AnsibleCreateLpgRouter $myLpgRouter $compartment $myVcn $myLPG

    sh 014_AddLpgRouteTableRules.sh     # calls a playbook that applies the correct routes to the tenant's LPG router tables
} # end function $ManageLpgRouters

Function ManageLPGs(
    )
{
    sh 012_CreateLPGs.sh
    sh 013_CreateLPGPeers.sh
} # end function ManageLPGs

Function ManageSubnets(
    [array]$mytenant,
    [array]$myTenantObject    
    )
{
    sh 011_CreateSubnets.sh
} # end function ManageSubnets


Function ManageVcns(
    [array]$mytenant,
    [array]$myTenantObject
    )
{
    $compartment        = GetActiveChildCompartment $myTenantObject $myTenant.AutomationCompartment
    CheckVcn $compartment $mytenant.AutomationVcnCidr
    $compartment        = GetActiveChildCompartment $myTenantObject $mytenant.BastionCompartmentName
    CheckVcn $compartment $mytenant.BastionVcnCidr
    $compartment        = GetActiveChildCompartment $myTenantObject $mytenant.DatabaseCompartmentName
    CheckVcn $compartment $mytenant.DatabaseVcnCidr
    $compartment        = GetActiveChildCompartment $myTenantObject $mytenant.TestCompartmentName
    CheckVcn $compartment $mytenant.TestVcnCidr
    $compartment        = GetActiveChildCompartment $myTenantObject $mytenant.WebCompartmentName
    CheckVcn $compartment $mytenant.WebVcnCidr
} # end function CreateVcn


