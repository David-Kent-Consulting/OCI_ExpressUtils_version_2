#!/usr/local/bin/pwsh
# nagios_swake.ps1

# use a param for long running jobs or jobs that must be run at a particular time and then switch according in the try function
param(
    [parameter(Mandatory=$true)]
        [string]$option
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

# Set the environment up from the JSON file environment.json
$timeStamp = Get-Date
#$LibPath = Get-ChildItem -Path env:ANSIBLE_LIB_PATH
#$Path = $LibPath.Value
$LibPath = "/Users/henrywojteczko/Documents/GitHub/NWMSU/master/test"
$Path = $LibPath

if (!$LibPath){
    Write-Output "ANSIBLE_LIB_PATH environment variable undefined. Please define and set to the path of the"
    Write-Output "DKC Ansible library and try again."
    Write-Output " "
    Write-Output "Hint: export ANSIBLE_LIB_PATH=/home/ansible/prod"
    Write-Output
    exit(1)
}
Set-Location $Path
Import-Module $Path/nagios.psm1                 # this is the DKC Nagios library, must load 1st
import-module $Path/DkcSolutionsOciLibrary.psm1 # this is the DKC library

$myEnv = Get-Content -Path "environment.json" | ConvertFrom-Json -AsHashtable
$Env:HOSTNAME = $myEnv.HOSTNAMEnagios_swake
$Env:ANSIBLE_LIB_PATH = $myEnv.ANSIBLE_LIB_PATH
$Env:PATH = $myEnv.PATH
$Env:HOME = $myEnv.HOME
$Env:XDG_DATA_DIRS = $myEnv.XDG_DATA_DIRS
$Env:PKG_CONFIG_PATH = $myEnv.PKG_CONFIG_PATH

# Classes

Class TenantObjects
{  
    [array]$TenantId
    [array]$AllParentCompartments
    [array]$ParentCompartment
    [array]$ChildCompartments
}

Class NagiosConfigurationFile
{
    [string]$command_file
    [string]$command_name
    [string]$command_line
    [string]$service_file
    [string]$use
    [string]$host_name
    [string]$service_description
    [string]$check_command

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
}

$networkObjects         = @{}

$vmObjects              = @{}

$NagiosConfigurationFile = [NagiosConfigurationFile]@{
                            command_file            = ''
                            command_name            = ''
                            service_file            = ''
                            use                     = ''
                            host_name               = ''
                            service_description     = ''
                            check_command           = ''
}

###########################################################################################################################
###     This is a sleep-wake program. It should be called by the service user ansible once every 10 minutes. It         ###
###     should create .txt files that are then read by a separate program by the service user nagios as the defined     ###
###     plugin. The name of this separate plugin is "nagios_plugin.ps1". The reason for this separation is two fold:    ###
###     1) A nagios plugin must respond in its entirity with a response within 10 seconds or is considered to be        ###
###         unresponsive.                                                                                               ###
###     2) We choose to handle the communications between this sleep-wake program and the program visible to nagios     ###
###         distinctly for security purposes.                                                                           ###
###                                                                                                                     ###
###     You should become familiar with the nagios developer guidelines at the URL below:                               ###
###     https://nagios-plugins.org/doc/guidelines.html                                                                  ###
###     And a nifty example of a shell plugin here:                                                                     ###
###     https://www.howtoforge.com/tutorial/write-a-custom-nagios-check-plugin/                                         ###
###     Check your config as in: sudo /usr/local/nagios/bin/nagios -v /usr/local/nagios/etc/nagios.cfg                  ###
###     WARNING! - DO NOT WRITE NAGIOS PLUGINS IN PERL, THERE HAVE BEEN NO SDK UPDATES SINCE 2017 FOR PERL AND THE SDK  ###
###     NEVER REACHED MATURITY.                                                                                         ###
###                                                                                                                     ###
###     See https://github.com/nagios-plugins for more info regarding the nagios project git site.                      ###
###                                                                                                                     ###
###     Any JSON files that are to be loaded should be defined as vars. Load your JSON files within functions to        ###
###     conserve RAM. Always use the "ConvertFrom-Json" and "-AsHashtable" methods to read the JSON data into           ###
###     dictionary objects. All output should be sent to $Path/logs as .txt files. Write to temporary files and then    ###
###     rewrite the destination file path. Always use the same temp file as defined in $TEMP_PATH and always do         ###
###     proper housekeeping by removing this temp file at the end of your function.                                     ###
###                                                                                                                     ###
###                                                                                                                     ###
###########################################################################################################################
# $TEMP_PATH          = $Path + '/logs/nagios_plugin_temp.txt'
# $DBAAS_FILE_PATH    = $Path + '/logs/dbsystems_statuses.txt'
# $DRG_FILE_PATH      = $Path + '/logs/drg_statuses.txt'
# $FILE_SERVICE_PATH  = $Path + '/logs/fileservice_statuses.txt'
# $IGW_FILE_PATH      = $Path + '/logs/igw_statuses.txt'
# $KBCLUSTER_FILE_PATH= $Path + '/logs/kbcluster_statuses.txt'
# $KBNODE_FILE_PATH   = $path + '/logs/kbnode_statuses.txt'
# $IPSEC_FILE_PATH    = $Path + '/logs/ipsec_statuses.txt'
# $NGW_FILE_PATH      = $Path + '/logs/natgw_statuses.txt'
# $SUBNET_FILE_PATH   = $Path + '/logs/subnet_statuses.txt'
# $VCN_FILE_PATH      = $Path + '/logs/vcn_statuses.txt'

# Functions 

##############################################################################################################
###         temporarily commented out whilst building this program                                         ###
##############################################################################################################
# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"

# Get basic tenant compartment data. The compartment ID drives everything in OCI, without it, you are DOA
$TenantObjects.TenantId                         = GetTenantId $tenant.TenantId
$TenantObjects.AllParentCompartments            =Get-ChildCompartments $TenantObjects.TenantId.data.id
$TenantObjects.ParentCompartment=(GetActiveParentCompartment $TenantObjects $tenant.ParentCompartmentName)
$TenantObjects.ChildCompartments = Get-ChildCompartments $TenantObjects.ParentCompartment.id

# Read the input JSON file for OCI objects to inspect
# The structure of the JSON file should be:
#   "Object Class":{
#       "compartmentNickName":{
#           "compartment_name": "oci name of compartment",
#           "object1_name":     "name of 1st object in this class to check",
#           "object2_name":     "name of 2nd object in this class to check",
#           ....
#           "last_object":      "last name of object to check"
#       },
#       "compartmentNichName:{
#           .....
#}
# so on, and so forth

# read the list of objects to check, in JSON format, and convert to hash tables
$myChecks = Get-Content -Path "nagios_swake.json" | ConvertFrom-Json -AsHashtable

try { 
    Write-Output "DKC Nagios Plug-in Sleep-Wake Process run start as of $timeStamp"
    Write-Output ""
    Write-Output "SW Collector running......"
    # call long running jobs or jobs that must be called separately from frequent checks within the switch
    # Always call the break method when doing this.
    # All jobs that must be run with frequency, aka every few minutes, should be in Default.
    # All frequent jobs must complete in less than 10 minutes since this sleep wake program will be called
    # every 15 minutes for frequent checks. If your job takes too long, work on your code or run it within
    # the switch.

    GetVCNObjects
    # $networkObjects

    Write-Output "SW Collector run completed. The collector will not run again until restarted."
    Write-Output ""
    $output = "Starting run at " + (Get-Date)
    Write-Output $output
    switch ($option){
        "BACKUP"        {
            GetVmObjects
            # $vmObjects
            CheckBackups $myChecks.backups $Path; break
        }
        "DATABASE"      {
            CheckDbNodes $Path
            CheckDbSystems $Path
        }
        "DRG"           {
            CheckDRGs $Path
        }
        "IGW"           {
            CheckIGWs $Path
        }
        "IPT"           {
            CheckIpTunnels $Path
        }
        "KBC"           {
            CheckKbCluster $Path
            CheckKbNodePools $Path
        }
        "NFS"           {
            CheckNfsService $Path
        }
        "NGW"           {
            CheckNatGw $Path
        }
        "SUBNET"        {
            CheckSubnets $Path
        }
        "VCN"           {
            checkVcns $Path
        }
        Default {
            Write-Output "Invalid option. Valid options are:"
            Write-Output "BACKUP - DATABASE - DRG - IGW - IPT - KBC - NFS - NGW - SUBNET - VCN"
            exit(1)
        }
    }
    $output = "Run ended at " + (Get-Date)
}
finally {
    $timeStamp = Get-Date
    Write-Output "DKC Nagios Plug-in Sleep-Wake Process Completed as of $timeStamp"
}

