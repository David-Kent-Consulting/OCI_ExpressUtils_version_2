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

# functions
Function AnsibleCreateLpgRouter(
    [string]$myLpgRouter,
    [array]$myCompartment,
    [array]$myVcn,
    [array]$myLPG
    )
{
    Write-Output "ansible-playbook 014_CreateLpgRouter.yaml --extra-var '{" `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Force
    $strng = '      "compartment_id":"'+$myCompartment.id+'",' `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Append
    $strng = '      "vcn_id":"'+$myVcn.data.id+'",' `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Append
    $strng = '      "display_name":"'+$myLpgRouter+'",' `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Append
    $strng = '      "cidr_block":"'+$myLPG.'peer-advertised-cidr'+'",' `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Append
    $strng = '      "network_entity_id":"'+$myLPG.id+'"' `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Append
    Write-Output "}'" `
            | Out-File -FilePath .\014_CreateLpgRouter.sh -Append
    Write-Output " "
    sh 014_CreateLpgRouter.sh
    Write-Output " "
    Write-Output "Check completed."
    Write-Output " "
    Remove-Item .\014_CreateLpgRouter.sh

} # end function AnsibleCreateLpgRouter


Function AnsibleCreateVcn(
    [string]$myCompartmentName,
    [string]$myCompartmentId,
    [string]$myVcnCidr
    )
{
    Write-Output "ansible-playbook 010_PrepareToCreateVCN.yaml --extra-var '{" `
        | Out-File -FilePath .\CreateVcn.sh -Force
    $strng = '      "CompartmentId":"'+$myCompartmentId+'",'
    Write-Output '      '$strng `
        | Out-File -FilePath .\CreateVcn.sh -Append
    $strng = '      "VcnDisplayName":"'+$myCompartmentName+'_vcn",'
    Write-Output '      '$strng `
        | Out-File -FilePath .\CreateVcn.sh -Append
    $strng = '      "VcnDnsName":"'+$myCompartmentName+'vcn",'
    Write-Output '      '$strng `
        | Out-File -FilePath .\CreateVcn.sh -Append
    $strng = '      "VcnCidr":"'+$myVcnCidr+'"'
    Write-Output '      '$strng `
        | Out-File -FilePath .\CreateVcn.sh -Append
    Write-Output "}'" `
        | Out-File -FilePath .\CreateVcn.sh -Append
    sh CreateVcn.sh
    Remove-Item .\CreateVcn.sh
    return
} # end function AnsibleCreateVcn

Function CheckSubnet(
    [array]$myCompartment,
    [string]$myCidr
    )
{
    $vcn                    = GetVcn $myCompartment | ConvertFrom-JSON -AsHashtable
    $subnet = GetSubnet $myCompartment $vcn
    if (!$subnet) {
        Write-Output "No subnet found within the VCN listed below" $vcn.data[0].'display-name'"creating the subnet now......"
        AnsibleCreateSubnet $myCompartment.name $myCompartment.id $vcn.data[0].id $myCidr
    }
} # end function CheckSubnet


Function CheckVcn(
    [array]$myCompartment,
    [string]$myVcnCidr
    )
{
    $vcn                = GetVcn $myCompartment
    if (!$vcn) {
        Write-Output "No virtual cloud network found for compartment"
        Write-Output "Creating VCN for CIDR Block  $myVcnCidr"
        Write-Output "......"
        AnsibleCreateVcn $myCompartment.name $myCompartment.'id' $myVcnCidr
    }
} # end function CheckVcn

Function Get-ChildCompartments (
    [string]$myParentCompartmentId
    )
{
    $myVal = oci iam compartment list --compartment-id $myParentCompartmentId 2> null
    $return = $myVal | ConvertFrom-Json -AsHashtable
    return $return
}

Function CopyBlockVolsInCompartment (
    [array]$myCompartment,
    [string]$mySourceRegion,
    [string]$myTargetRegion
)
{
    $myBlockVolList  = oci bv backup list `
                        --compartment-id $myCompartment.id `
                        --region $mySourceRegion `
                        --all `
                        | ConvertFrom-Json -AsHashtable
    $count          = $myBlockVolList.data.count
    $myTargetBlockVolList = oci bv backup list `
    --compartment-id $myCompartment.id `
    --region $myTargetRegion `
    --all `
    | ConvertFrom-Json -AsHashtable
    
    $cntr           = 0
     while ($cntr -lt $count) {
         if ($myBlockVolList.data[$cntr].'lifecycle-state' -eq "AVAILABLE"){
            if ($myBlockVolList.data[$cntr].'lifecycle-state' -eq "AVAILABLE") {
                $item_found = $false
                # here is the critical logic. Regression search for display-name between all SNAP images in target region versus
                # what is in the source region. If found, we set $item_found to true and fall through to the next item in the list,
                # if not found, $item_found remains false and we execute the code to copy the item to the target region.
                foreach ( $item in $myTargetBlockVolList.data ){
                    if ( $item.'display-name' -eq $myBlockVolList.data[$cntr].'display-name' ){
                        $item_found = $true
                    }
                }
                if (!$item_found){
                    $image_item = $myBlockVolList.data[$cntr].'display-name'
                    Write-Output "copying backup SNAP $image_item to $myTargetRegion"
                    $return = oci bv backup copy `
                        --volume-backup-id $myBlockVolList.data[$cntr].id `
                        --region $mySourceRegion `
                        --destination-region $myTargetRegion `
                        | ConvertFrom-Json -AsHashtable
                        if (!$return) {
                            Write-Output "WARNING! - Failed to Copy Backup Resource."
                            Write-Output " "
                        } else {
                            #$myVolume = $myBlockVolList.data[$cntr].'display-name'
                            #Write-Output "Backup volume copy to region $myTargetRegion started for volume $myVolume"
                            $loop = "continue"
                            $myCount = 0
                            while ($loop -eq "continue"){
                                Start-Sleep 60
                                $myBackupState = oci bv backup copy `
                                    --volume-backup-id $myBlockVolList.data[$cntr].id `
                                    --region $mySourceRegion `
                                    --destination-region $myTargetRegion `
                                    | ConvertFrom-Json -AsHashtable
                                if ( $myBackupState.data.'lifecycle-state' -eq "AVAILABLE" ) {
                                    Write-Output " "
                                    Write-Output "Volume copy of $myVolume completed without issues."
                                    Write-Output $myBackupState.data
                                    $loop = "exit"
                                } else {
                                    $myCount = $myCount+1
                                    if ( $myCount -gt 119){
                                        Write-Output "WARNING! Volume copy failed after 2 hours. Please check the OCI logs for more information."
                                        $loop = "exit"
                                    }
                                }
                            }
                        }
                }
            }
         }
         $cntr = $cntr+1
     }
} # end function CopyBlockVolsInCompartment

Function CopyBootVolsInCompartment (
    [array]$myCompartment,
    [string]$mySourceRegion,
    [string]$myTargetRegion
)
{
    $myBootVolList  = oci bv boot-volume-backup list `
                        --compartment-id $myCompartment.id `
                        --region $mySourceRegion `
                        --all `
                        | ConvertFrom-Json -AsHashtable
    #$myBootVolList.data
    $myTargetBootVolList = oci bv boot-volume-backup list `
                        --compartment-id $myCompartment.id `
                        --region $myTargetRegion `
                        --all `
                        | ConvertFrom-Json -AsHashtable
    #$myTargetBootVolList.data
    $count          = $myBootVolList.data.count
    $cntr           = 0
    while ($cntr -lt $count) {
        $item_found = $false
        if ($myBootVolList.data[$cntr].'lifecycle-state' -eq "AVAILABLE"){
            # here is the critical logic. Regression search for display-name between all SNAP images in target region versus
            # what is in the source region. If found, we set $item_found to true and fall through to the next item in the list,
            # if not found, $item_found remains false and we execute the code to copy the item to the target region.
            foreach ( $item in $myTargetBootVolList.data ) {
                if ( $item.'display-name' -eq $myBootVolList.data[$cntr].'display-name' ) {
                    $item_found = $true
                }
            }
            if (!$item_found) {
                $image_name = $myBootVolList.data[$cntr].'display-name'
                Write-Output "copying backup SNAP $image_name to $myTargetRegion"
                $return = oci bv boot-volume-backup copy `
                         --boot-volume-backup-id $myBootVolList.data[$cntr].id `
                         --region $mySourceRegion `
                         --destination-region $myTargetRegion `
                         | ConvertFrom-Json -AsHashtable
                if ($return) {
                    $loop = "continue"
                    $myCount = 0
                    while ($loop -eq "continue"){
                        Start-Sleep 60
                        $myBackupState = oci bv boot-volume-backup copy `
                            --boot-volume-backup-id $myBootVolList.data[$cntr].id `
                            --region $mySourceRegion `
                            --destination-region $myTargetRegion `
                            | ConvertFrom-Json -AsHashtable
                        if ( $myBackupState.data.'lifecycle-state' -eq "AVAILABLE" ) {
                            Write-Output " "
                            Write-Output "Volume copy of $myVolume completed without issues."
                            Write-Output $myBackupState.data
                            $loop = "exit"
                        } else {
                            $myCount = $myCount+1
                            if ( $myCount -gt 119) {
                                Write-Output "WARNING! Volume copy failed after 2 hours. Please check the OCI logs for more information."
                                $loop = "exit"
                            }
                        }
                    }
                } else {
                    Write-Output "WARNING! - Failed to Copy Backup Resource."
                    Write-Output " "
                }
            }
        }
        $cntr = $cntr+1
    }
} # end function CopyBootVolsInCompartment
Function GetActiveChildCompartment (
        [array]$myCompartmentId,
        [string]$myCompartment
    )
{

    $count = $myCompartmentId.ChildCompartments.data.Count
    $cntr  = 0
    while ( $cntr -lt $count)
    {
        $myVal = $myCompartmentId.ChildCompartments.data[$cntr].'lifecycle-state'
        if ( $myCompartmentId.ChildCompartments.data[$cntr].'name' -eq $myCompartment -and $myVal -eq "ACTIVE" )
        {
            return $myCompartmentId.ChildCompartments.data[$cntr]
        }
        $cntr=$cntr+1
    }
} # end Function GetActiveChildCompartment

Function GetActiveParentCompartment (
        [array]$myCompartmentId,
        [string]$myCompartment
    )
{
    $count = $myCompartmentId.AllParentCompartments.data.Count
    $cntr  = 0
    while ( $cntr -lt $count)
    {
        $myVal = $myCompartmentId.AllParentCompartments.data[$cntr].'lifecycle-state'
        if ( $myCompartmentId.AllParentCompartments.data[$cntr].'name' -eq $myCompartment -and $myVal -eq "ACTIVE" )
        {
            return $myCompartmentId.AllParentCompartments.data[$cntr]
        }
        $cntr=$cntr+1
    }
} # end Function GetActiveParentCompartment

function GetAvailabilityDomains(
    [parameter(Mandatory=$true)]
        [string]$myRegion
){
    $return = oci iam availability-domain list --region $myRegion `
        | ConvertFrom-Json -AsHashTable
    return($return)
}
Function GetBackupPolicies(
    [array]$myCompartment,
    [string]$myRegion
)
{
  $return               = oci bv volume-backup-policy list `
                          --compartment-id $myCompartment.id `
                          --region $myRegion `
                          | ConvertFrom-Json -AsHashtable
  return($return)
} # end function GetBackupPolicies

Function GetBlockVolumes(
    [array]$myVM,
    [string]$myRegion
)
{
    $return     = oci compute volume-attachment list `
                    --compartment-id $myVM.'compartment-id' `
                    --availability-domain $myVM.'availability-domain' `
                    --region $myRegion `
                    | ConvertFrom-Json -AsHashtable
    return($return)
} # end function GetBlockVolume

Function GetBootVolumes(
    [array]$myVM,
    [string]$myRegion
)
{
    $return     = oci compute boot-volume-attachment list `
                    --compartment-id $myVM.'compartment-id' `
                    --availability-domain $myVM.'availability-domain' `
                    --region $myRegion `
                    | ConvertFrom-Json -AsHashtable
    return($return)
} # end function GetBootVolume

function GetCluster(
  [array]$myCompartment,
  [string]$myClusterName,
  [string]$myRegion
)
{
    $clusters = oci ce cluster list `
                --compartment-id $myCompartment.id `
                --region $myRegion `
                | ConvertFrom-Json -AsHashtable
    #$clusters.data
    $count = $clusters.data.count
    $cntr = 0
    while ( $cntr -le $count ){
      if ( $clusters.data[$cntr].name -eq $myClusterName -and $clusters.data[$cntr].'lifecycle-state' -ne 'DELETED' ){
        return($clusters.data[$cntr])
      }
      $cntr=$cntr+1
    }
} # end function GetClusters

Function GetDbSystems(
    [array]$myCompartment,
    [string]$myDbSystemName,
    [string]$myRegion
    )
{
    $return   = oci db system list `
                    --compartment-id $myCompartment.id `
                    --region $myRegion `
                    | ConvertFrom-JSON -AsHashTable
    return($return)

} # end function GetDbSystems

Function GetDbNodeName (
    [array]$myDbSystems,
    [string]$myDbNodeName,
    [string]$myRegion
    )
{
    $count      = $myDbSystems.data.Count
    $cntr       = 0
    while ( $cntr -lt $count) {
        if ( $myDbSystems.data[$cntr].hostname -eq $myDbNodeName -and $myDbSystems.data[$cntr].'lifecycle-state' -ne "TERMINATED") {
          $return = oci db node list `
          --compartment-id $myDbSystems.data[$cntr].'compartment-id' `
          --db-system-id $myDbSystems.data[$cntr].id `
          --region $myRegion `
          | ConvertFrom-Json -AsHashtable
          return($return.data)
        }
        $cntr   = $cntr+1
    }
    if ( $myDbSystems.data.hostname -eq $myDbNodeName -and $myDbSystems.'lifecycle-state' -ne "TERMINATED" ) {
        return ($myDbSystems.data)
    }
} # end function GetDbNodeName

function GetDRGs {
    param (
        [parameter(Mandatory=$true)]
            [array]$myVcn,
            [string]$myRegion
    )
    $return = oci network drg list `
        --compartment-id $myVcn.'compartment-id' `
        --all `
        --region $myRegion `
        | ConvertFrom-Json -AsHashtable
    return($return)
}# end function GetDrg

function GetFileSystems(
    [array]$myCompartment,
    [string]$myAvailabilityDomain,
    [string]$myRegion
)
{
    $result = oci fs file-system list `
    --compartment-id $myCompartment.id `
    --availability-domain $myAvailabilityDomain `
    --all `
    --region $myRegion `
    | ConvertFrom-Json -AsHashtable
    return($result)
} # end function GetFileSystems

function GetFileSystem(
    [array]$myFileSystems,
    [string]$myFileSystemName
)
{
    foreach ($return in $myFileSystems.data){
        if ($return.'display-name' -eq $myFileSystemName -and $return.'lifecycle-state' -ne 'TERMINATED'){
            return($return)
        }
    }
} # end function GetFileSystem

function GetGroups(
    [string]$tenant_id
){
    $result = oci iam group list `
            --compartment-id $tenant_id `
            | ConvertFrom-Json -AsHashtable
    return($result)
} # end function GetGroups

function GetGroup(
    [array]$myGroups,
    [string]$myGroupName
){
    $count = $myGroups.data.count
    $cntr  = 0
    while ($cntr -le $count) {
        #Write-Output $myGroups.data[$cntr].name
        if ($myGroups.data[$cntr].name -eq $myGroupName) {return $myGroups.data[$cntr]}
        $cntr = $cntr+1
    }
} # end function GetGroup
function GetIGWs
(
    [array]$myVcn,
    [string]$myRegion
){
    $return = oci network internet-gateway list `
        --compartment-id $myVcn.'compartment-id' `
        --vcn-id $myVcn.id `
        --region $myRegion `
        --all `
        | ConvertFrom-Json -AsHashtable
    return($return)
}# end function GetIGWs

function GetIpSecConnections(
    [parameter(Mandatory=$true)]
        [array]$myCompartment,
    [parameter(Mandatory=$true)]
        [string]$myRegion
){
    # $myCompartment
    # $myRegion
    oci network ip-sec-connection list `
        --compartment-id $myCompartment.id `
        --region $myRegion `
        | ConvertFrom-Json -AsHashtable
    return ($return)
}# end function GetIpSecConnections

function GetIpSecTunnels(
    [array]$myIpSecConnection
){
    $return = oci network ip-sec-tunnel list `
        --ipsc-id $myIpSecConnection.id `
        --all `
        | ConvertFrom-Json -AsHashtable
    return($return)
}# end function GetIpSecTunnels

Function GetLPGs(
    [array]$myVcn
    )
{
    if ($myvcn.data.'compartment-id') {
        $return = oci network local-peering-gateway list `
            --compartment-id $myvcn.data.'compartment-id' `
            --vcn-id $myVcn.data.id `
            | ConvertFrom-Json -AsHashTable
        return($return)
    }
    if ($myvcn.'compartment-id')
    {
        $return = oci network local-peering-gateway list `
            --compartment-id $myvcn.'compartment-id' `
            --vcn-id $myVcn.id `
            | ConvertFrom-Json -AsHashTable
        return($return)
    }

} # end function GetLPGs

function GetKbClusters(
    [parameter(Mandatory=$true)]
        [array]$myCompartment,
    [parameter(Mandatory=$true)]
        [string]$myRegion
){
    $return = oci ce cluster list `
        --compartment-id $myCompartment.id `
        --region $myRegion `
        --all `
        | ConvertFrom-Json -AsHashtable
    return($return)
}
function GetMountTargets(
  [array]$myCompartment,
  [string]$myAvailabilityDomain,
  [string]$myRegion
){
    $result = oci fs mount-target list `
            --compartment-id $myCompartment.id `
            --availability-domain $myAvailabilityDomain `
            --all `
            --region $myRegion `
            | ConvertFrom-Json -AsHashtable
    return($result)
} # end function GetMountTargets

function GetMountTarget(
  [array]$myMountTargets,
  [string]$myMountTargetName
){
    foreach ($return in $myMountTargets.data){
        if ($return.'display-name' -eq $myMountTargetName -and $return.'lifecycle-state' -ne 'TERMINATED'){
            return($return)
        }
    }
}# end function GetMountTarget

function GetNatGWs(
    [parameter(Mandatory=$true)]
        [array]$myVCN,
    [parameter(Mandatory=$true)]
        [string]$myRegion
){
    $return = oci network nat-gateway list `
        --compartment-id $myVCN.'compartment-id' `
        --region $myRegion `
        --all `
        | ConvertFrom-Json -AsHashtable
    return($return)
}
function GetNetSecurityGroup(
    [array]$myCompartment,
    [string]$myNetworkSecurityGroup,
    [string]$myRegion
){
    $nsg_list   = oci network nsg list `
                    --compartment-id $myCompartment.id `
                    --region $myRegion `
                    | ConvertFrom-Json -AsHashtable
    foreach ( $n in $nsg_list.data) {
        if ( $n.'display-name' -eq $myNetworkSecurityGroup `
                -and $n.'lifecycle-state' -eq "AVAILABLE" ) {return $n}
    }
    
} # end function GetNetSecurityGroups

function GetNodePool(
    [array]$myCluster,
    [string]$myNodePoolName,
    [string]$myRegion
){
    #$myCluster.'compartment-id'
    $nodepool_list = oci ce node-pool list `
                    --compartment-id $myCluster.'compartment-id' `
                    --region $myRegion `
                    | ConvertFrom-Json -AsHashtable
    #$nodepool_list
    foreach ($nodepool in $nodepool_list.data){
        if ($nodepool.name -eq $myNodePoolName -and $nodepool.'lifecycle-state' -ne 'TERMINATED'){
            return($nodepool)
        }
    }
} # end function GetNodePool

Function GetRouteTable(
    [array]$myVcn
    )
{
    if ($myvcn.data.'compartment-id') {
        $return             = oci network route-table list `
        --compartment-id $myVcn.data.'compartment-id' `
        --vcn-id $myVcn.data.id `
        | ConvertFrom-Json -AsHashTable
        return($return)
    }
    if ($myvcn.'compartment-id')
    {
        $return             = oci network route-table list `
        --compartment-id $myVcn.'compartment-id' `
        --vcn-id $myVcn.id `
        | ConvertFrom-Json -AsHashTable
        return($return)
    }
} # end function GetRouteTables

Function GetSubnet(
    [array]$myCompartment,
    [array]$myVcn,
    [string]$myRegion
    )
{
    if ($myVcn.data.id)
    {
        $return = oci network subnet list `
        --compartment-id $myCompartment.id `
        --vcn-id $myVcn.data.id `
        --region $myRegion `
        --all `
        | ConvertFrom-JSON -AsHashtable
        return($return)
    }
    if ($myVcn.id)
    {
        $return = oci network subnet list `
        --compartment-id $myCompartment.id `
        --vcn-id $myVcn.id `
        --region $myRegion `
        --all `
        | ConvertFrom-JSON -AsHashtable
        return($return)
    }
} # end function GetSubnet


Function GetTenantId (
        [string]$myTenantId
    )
{
    $return = oci iam compartment get --compartment-id $myTenantId | ConvertFrom-Json 2> null
    if ($return) {
        return $return
    } else {
        Write-Output "Warning! Tenant ID $myTenantId not found. Script aborting."
        exit 9
    }
}

Function GetVcn(
    [array]$myCompartment,
    [string]$myRegion
    )
{
    if (!$myRegion) { 
      $return = oci network vcn list --compartment-id $myCompartment.id | ConvertFrom-Json
    } else {
      $return = oci network vcn list --compartment-id $myCompartment.id --region $myRegion `
        | ConvertFrom-Json
    }
    return($return)
} # end function GetVcn

Function GetVM(
    [array]$myVMs,
    [string]$myVmName
)
{
    $count      = $myVMs.data.count
    $cntr       = 0
    while ( $cntr -lt $count) {
        if ( $myVMs.data[$cntr].'display-name' -eq $myVmName -and $myVMs.data[$cntr].'lifecycle-state' -ne "TERMINATED" ) {
            return($myVMs.data[$cntr])
        }
        $cntr   = $cntr+1
    }
    if ( $myVMs.data.'display-name' -eq $myVmName -and $myVMs.data.'lifecycle-state' -ne "TERMINATED" ) { return($myVMs.data) }
} # end function GetVM

Function GetVMs (
    [array]$myCompartment,
    [string]$myRegion
    )
{
    $return                     = oci compute instance list `
                                 --compartment-id $myCompartment.id `
                                 --region $myRegion `
                                 --all `
                                 | ConvertFrom-Json -AsHashTable
    return($return)
} # end function GetVMs

function GetVnic(
    [array]$myVm,
    [string]$myRegion
){
    $vnics_in_compartment = oci compute vnic-attachment list `
                            --compartment-id $myVm.'compartment-id' `
                            --availability-domain $myVm.'availability-domain' `
                            --instance-id $myVm.id `
                            --region $myRegion `
                            | ConvertFrom-Json -AsHashtable
    return ($vnics_in_compartment)
} # end function GetVnic

Function GetVmNicAttachment (
    [array]$myVM,
    [string]$myRegion
)
{
    $myNicList = oci compute vnic-attachment list `
        --compartment-id $myVM.'compartment-id' `
        --availability-domain $myVM.'availability-domain' `
        --region $myRegion `
        | ConvertFrom-Json -AsHashtable
    if (!$myNicList) {return}
    $count  = $myNicList.data.Count
    $cntr   = 0
    while ( $cntr -lt $count ){
        if ( $myNicList.data[$cntr].'instance-id' -eq $myVM.id -and $myNicList.data[$cntr].'lifecycle-state' -eq "ATTACHED") {
            return( $myNicList.data[$cntr] )
        }
        $cntr = $cntr+1
    }
} # end function GetVmNicAttachment

Function GetVmBootVolBackups(
    [array]$myCompartment,
    [string]$myRegion
)
{
    $return     = oci bv boot-volume-backup list `
                    --compartment-id $myCompartment.id --all `
                    --region $myRegion `
                    | ConvertFrom-Json -AsHashtable
    return( $return )
} # end function GetVmBootVolBackups

Function GetVmBlockVolBackups(
    [array]$myCompartment,
    [string]$myRegion
)
{
    $return     = oci bv backup list `
                    --compartment-id $myCompartment.id --all `
                    --region $myRegion `
                    | ConvertFrom-Json -AsHashtable
    return( $return )
} # end function GetVmBlockVolBackups

function GetUsers(
    [string]$tenant_id
)
{
    $return = oci iam user list `
            --compartment-id $tenant_id `
            | ConvertFrom-Json -AsHashtable
    return($return)
} # end function GetUsers

function GetUser(
    [array]$myUsers,
    [string]$myUserName
){
    $count = $myUsers.data.count
    $cntr  = 0
    while ($cntr -le $count){
        #Write-Output $myUsers.data[$cntr].name
        if ($myUsers.data[$cntr].name -eq $myUserName ) {return($myUsers.data[$cntr])}
        $cntr = $cntr+1
    }
} # end function GetUser
Function GetBlockVolumes(
    [array]$myVM
)
{
    $return     = oci compute volume-attachment list `
                    --compartment-id $myVM.'compartment-id' `
                    --availability-domain $myVM.'availability-domain' `
                    | ConvertFrom-Json -AsHashtable
    return($return)
} # end function GetBlockVolume


Function ReadCsv(
    [string]$FileName)
{
    $dfield = ";" -as [char]                    # set the char deliminter type, 09 is a tab
    # Imports the Tab Delimited file and adds headers so the data can be easily found
    $File = Import-CSV -Path $FileName -Delimiter $dfield -Header C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16
    return $File
} # end function ReadCsv

Function RestoreBootVol (
    [array]$myVolToRestore,
    [array]$myVmName,
    [array]$myNewVmName,
    [string]$myRegion
)
{
    $myVolToRestore
    Write-Output " "
    $myVmName
    Write-Output " "
    $myNewVmName
    $return = oci bv boot-volume create `
        --compartment-id $myVmName.'compartment-id' `
        --availability-domain $myVmName.'availability-domain' `
        --display-name $myNewVmName' (Boot Volume)' `
        --boot-volume-backup-id $myVolToRestore.id `
        --size-in-gbs $myVolToRestore.'size-in-gbs' `
        --region $myRegion `
        --wait-for-state "AVAILABLE" `
        | ConvertFrom-Json -AsHashtable
    if (!$return) {
        Write-Output " "
        Write-Output "WARNING! Failed to restore volume from the latest backup. Check your configuration"
        Write-Output "and if necessary, open a support request at"
        Write-Output "https://support.oracle.com"
        Write-Output " "
        return 1
    } else {
        Write-Output " "
        Write-Output "Volume restored"
        return($return)
    }
}# end function RestoreBootVol

# function ReturnDataValWithOptions to be used to return values when oci CLI utility returns JSON in [data] array
Function ReturnDataValWithOptions(
    [string]$myProgramName,
    [array]$myReturnValue,
    [string]$myOption
    )
{
    if (!$myOption){
        return 1
    } else {
        switch ( $myOption){
            'ALL'           {return($myReturnValue.data)}
            'COMPARTMENT'   {return($myReturnValue.data.'compartment-id')}
            'DISPLAYNAME'   {return($myReturnValue.data.'display-name')}
            'OCID'          {return($myReturnValue.data.id)}
            default{
                            Write-Output " "
                            Write-Output "$myProgramName :  Invalid option, valid values are:"
                            Write-Output "ALL - returns all resource data"
                            Write-Output "COMPARTMENT - Returns compartment ID where resource resides"
                            Write-Output "DISPLAYNAME - Returns display name of resource"
                            Write-Output "OCID - Returns OCID of resource"
                            Write-Output " "
                            Write-Output " "
                            return 1
            }

        }
    }
    
} # end function ReturnDataValWithOptions

# function ReturnValWithOptions to be used to return values when oci CLI utility returns JSON without [data] array
Function ReturnValWithOptions(
    [string]$myProgramName,
    [array]$myReturnValue,
    [string]$myOption
    )
{
    if (!$myOption){
        return 1
    } else {
        switch ( $myOption){
            'ALL'           {return($myReturnValue)}
            'BOOTVOLID'     {return($myReturnValue.'boot-volume-id')}
            'BLOCKVOLID'    {return($myReturnValue.'volume-id')}
            'COMPARTMENT'   {return($myReturnValue.'compartment-id')}
            'DISPLAYNAME'   {return($myReturnValue.'display-name')}
            'OCID'          {return($myReturnValue.id)}
            default{
                            Write-Output " "
                            Write-Output "$myProgramName :  Invalid option, valid values are:"
                            Write-Output "ALL - returns all resource data"
                            Write-Output "BOOTVOLID - Returns the VM's attached boot volume"
                            Write-Output "COMPARTMENT - Returns compartment ID where resource resides"
                            Write-Output "DISPLAYNAME - Returns display name of resource"
                            Write-Output "OCID - Returns OCID of resource"
                            Write-Output " "
                            Write-Output " "
                            return ($false)
            }

        }
    }
    
} # end function ReturnValWithOptions


Function SelectBackupPolicy(
  [array]$myBackupPolicies,
  [string]$myBackupPolicyName
)
{
  $count                = $myBackupPolicies.data.Count
  $cntr                 = 0
  while ( $cntr -lt $count) {
    if ( $myBackupPolicies.data[$cntr].'display-name' -eq $myBackupPolicyName ) { return($myBackupPolicies.data[$cntr]) }
    $cntr                = $cntr+1
  }
  if ( $myBackupPolicies.data.'display-name' -eq $myBackupPolicyName ) { return($myBackupPolicies.data )} # Oracle JSON conversion to dictionary object inconsistent when 1 array object returned
                                                                                                                        # this is how we deal with it.
} # end function SelectBackupPolicy

Function SelectBlockVolume(
    [array]$myVM,
    [array]$myBlockVolumes
)
{
    $count      = $myBlockVolumes.data.count
    $cntr       = 0
    while ( $cntr -lt $count ){
        if ( $myBlockVolumes.data[$cntr].'instance-id' -eq $myVm.id -and $myBlockVolumes.data[$cntr].'lifecycle-state' -eq 'ATTACHED' ) {
            return $myBlockVolumes.data[$cntr]
        }
        $cntr   = $cntr+1
    }
    if ( $myBlockVolumes.data.'instance-id' -eq $myVm.id -and $myBlockVolumes.data.'lifecycle-state' -eq "ATTACHED" ) { return($myBlockVolumes.data  ) }
} # end function SelectBlockVolume

Function SelectBootVolume(
    [array]$myVM,
    [array]$myBootVolumes
)
{
    $count      = $myBootVolumes.data.count
    $cntr       = 0
    while ( $cntr -lt $count ){
        if ( $myBootVolumes.data[$cntr].'instance-id' -eq $myVm.id ) {
            return $myBootVolumes.data[$cntr]
        }
        $cntr   = $cntr+1
    }
    if ( $myBootVolumes.data.'instance-id' -eq $myVm.id ) { return($myBootVolumes.data) }
} # end function SelectBootVolume

function SelectDbSystem(        # we must select like this to ensure we get a complete list of DB system in all possible lifecycle states
    [string]$myDbSystemName,
    [array]$myDbSystems
){
    foreach ($dbSystem in $myDbSystems.data){
        if ($dbSystem.'display-name' -eq $myDbSystemName){
            return $dbSystem
        }
    }
}# end function SelectDbSystem

function SelectDRG {
    param (
        [Parameter(Mandatory=$true)]
            [array]$myDRGs,
        [parameter(Mandatory=$true)]
            [string]$myDRgName
    )
    foreach ($item in $myDRGs.data){
        if ($item.'display-name' -eq $myDRgName -and $item.'lifecycle-state' -ne 'TERMINATED'){
            return($item)
        }
    }
}# end function SelectDRG

function SelectIGW(
    [string]$myIgwName,
    [array]$myIGWs
)
{
    $count      = $myNGWs.data.$count
    $cntr       = 0
    while ( $cntr -lt $count ){
        if ( $myIGWs.data[$cntr].'display-name' -eq $myIgwName ){
            return $myIGWs.data[$cntr]
        }
    }
    if ( $myIGWs.data.'display-name' -eq $myIgwName ) { return $myIGWs.data}
} # end function SelectIGW

function SelectIpSecTunnel(
        [array]$myIpsecConnections,
        [string]$myIpSecConnectionName
){
    $myIpsecConnections
    $myIpSecConnectionName
    foreach ($item in $myIpsecConnections.data){
        if ($item.'lifecycle-state' -ne 'TERMINATED' -and $item.'display-name' -eq $myIpSecConnectionName){
            return($item)
        }
    }
}# end SelectIpSecTunnel

function SelectKbCluster(
    [parameter(Mandatory=$true)]
        [array]$myKbClusters,
    [parameter(Mandatory=$true)]
        [string]$myKbClusterName
){
    foreach ($return in $myKbClusters.data){
        if ($return.name -eq $myKbClusterName ` -and $return.'lifecycle-state' -ne 'TERMINATED'){
            return($return)
        }
    }
}# end function SelectKbCluster
Function SelectLPG(
    [string]$myLpgName,
    [array]$myLPGs
    )
{
    $count = $myLPGs.data.Count
    $cntr=0
    while ( $cntr -lt $count) {
        if ( $myLPGs.data[$cntr].'display-name' -eq $myLpgName) {
            return($myLPGs.data[$cntr])
        }
        $cntr=$cntr+1
    }

} # end function SelectLPG

function SelectNGW(
    [string]$myNgwName,
    [array]$myNGWs
)
{
    foreach ($myNatGW in $myNGWs.data){
        if ($myNatGW.'display-name' -eq $myNgwName -and $myNatGW.'lifecycle-state' -ne 'TERMINATED'){
            return($myNatGW)
        }
    }
} # end of function SelectNGW
Function SelectRouterTable(
    [string]$myRouterTableName,
    [array]$myRouterTables
    )
{
    $count = $myRouterTables.data.Count
    $cntr=0
    while ( $cntr -lt $count) {
        if ( $myRouterTables.data[$cntr].'display-name' -eq $myRouterTableName) {
            return $myRouterTables.data[$cntr]
        }
        $cntr = $cntr+1
    }
} # end function SelectRouterTable


Function SetLpgContext(
    [string]$myLpg,
    [array]$myLPGs
    )
{
    $count = $myLPGs.data.Count
    $cntr=0
    while ( $cntr -lt $count )
    {
        if ( $myLPGs.data[$cntr].'display-name' -eq $myLpg ) {
            return( $myLPGs.data[$cntr] )
        }
        $cntr=$cntr+1
    }
} # end function SetLpgContext

function SelectSecList(
    [string]$mySecurityListName,
    [array]$mySecLists
){
    $count = $mySecLists.data.$count
    $cntr  = 0
    while ($cntr -le $count ){
        if ( $mySecLists.data[$cntr].'display-name' -eq $mySecurityListName -and $mySecLists.data[$cntr].'lifecycle-state' -eq 'AVAILABLE' ){
            return $mySecLists.data[$cntr]
        }
    }
    if ( $mySecLists.data.'display-name' -eq $mySecurityListName -and $mySecLists.data[$cntr].'lifecycle-state' -eq 'AVAILABLE' ) { return $mySecLists.data }
} # end function SelectSecList

Function SelectSubnet(
  [array]$mySubnets,
  [string]$mySubNetName
)
{
  $count        = $mySubnets.data.Count
  $cntr = 0
  while ( $cntr -lt $count) {
   if ( $mySubnets.data[$cntr].'display-name' -eq $mySubNetName ) { return($mySubnets.data[$cntr]) }
   $cntr       = $cntr+1
  }
  if ( $mySubnets.data.'display-name' -eq $mySubNetName ) {return($mySubnets.data)} # Oracle JSON conversion to dictionary object inconsistent when 1 array object returned
                                                                                    # this is how we deal with it.
} # end function SelectSubnet


Function SelectVcn(
    [string]$myVcnName,
    [array]$myVCNs
)
{
    $count      = $myVCNs.data.count
    $cntr       = 0
    while ( $cntr -lt $count ){
        if ( $myVCNs.data[$cntr].'display-name' -eq $myVcnName ) { return($myVCNs.data[$cntr]) }
        $cntr       = $cntr+1
    }
    if ( $myVCNs.data.'display-name' -eq $myVcnName ) { return($myVCNs.data )}  # Oracle JSON conversion to dictionary object inconsistent when 1 array object returned
                                                                                                # this is how we deal with it.
}

# Left here, erroneous, must make sure nothing is using it prior to removing from library
# Wojteczko 06-apr-2020
Function SelectVnc(
  [array]$myVCNs,
  [string]$myVcnName
)
{
  $count        = $myVCNs.data.Count
  $cntr         = 0
    while ( $cntr -lt $count ){
    if ( $myVCNs.data[$cntr].'display-name' -eq $myVcnName ) { return($myVCNs.data[$cntr]) }
    $cntr       = $cntr+1
  }
  if ( $myVCNs.data[$cntr].'display-name' -eq $myVcnName ) { return($myVCNs.data[$cntr] )}  # Oracle JSON conversion to dictionary object inconsistent when 1 array object returned
                                                                                            # this is how we deal with it.
} # end function SelectVnc 

