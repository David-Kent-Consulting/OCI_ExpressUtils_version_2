#!/usr/local/bin/pwsh
param(
    [parameter(Mandatory=$true)]
        [string]$options,
    [parameter(Mandatory=$false)]
        [string]$file
)

# nagios_vcn.ps1 plugin
# I have not figured out why nagios is ignoring the environment yet and so am hard setting in the code for now
# Yah, it is an ugly thing
$LibPath = "/Users/henrywojteczko/Documents/GitHub/NWMSU/master/test"     
#$Path = $LibPath.Value
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
import-module $Path/DkcSolutionsOciLibrary.psm1 # this is the DKC library
$myEnv = Get-Content -Path $Path/environment.json | ConvertFrom-Json -AsHashtable
$Env:HOSTNAME = $myEnv.HOSTNAME
$Env:ANSIBLE_LIB_PATH = $myEnv.ANSIBLE_LIB_PATH
$Env:PATH = $myEnv.PATH
$Env:HOME = $myEnv.HOME
$Env:XDG_DATA_DIRS = $myEnv.XDG_DATA_DIRS
$Env:PKG_CONFIG_PATH = $myEnv.PKG_CONFIG_PATH





# functions
function reportStatuses(
    [parameter(Mandatory=$true)]
        [string]$myFileName
)
{
    $ERROR_STATE = $false
    $FILE_PATH = $Path + '/logs/' + $myFileName
    if (Test-Path -Path $FILE_PATH){
        $arrayFromFile = @(Get-Content -Path $FILE_PATH)
        if ($arrayFromFile[0] -ne 'OK') {
            $ERROR_STATE = $true
            switch($arrayFromFile[0]){
                "WARNING"   {$rc = 1}
                "CRITICAL"  {$rc = 2}
                default     {$rc = 9}

            }
        }
    } else {
        Write-Output "file not found"
        exit(9)
    }
    $count = $arrayFromFile.Count
    $cntr=0
    while ( $cntr -le $count-1){
        if ($cntr -eq 0){
            $output = $arrayFromFile[$cntr] + ' - ' + $arrayFromFile[$cntr+1]
            Write-Output $output
            $cntr=$cntr+2
        } else {
            $output = $arrayFromFile[$cntr]
            Write-Output $output
            $cntr=$cntr+1
        }
    }
    if ($ERROR_STATE){exit($rc)}
}


##############################################################################################################
###         temporarily commented out whilst building this program                                         ###
##############################################################################################################
# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "TRUE"
$env:SUPPRESS_PYTHON2_WARNING = "TRUE"
$ERROR_STATE = $false



switch ($options) {
    "BACKUP"    {reportStatuses $file}
    "DBAAS"     {reportStatuses 'dbsystems_statuses.txt'}
    "DBNODE"    {reportStatuses $file}
    "DRG"       {reportStatuses 'drg_statuses.txt'}
    "FSERVICE"  {reportStatuses 'fileservice_statuses.txt'}
    "IGW"       {reportStatuses 'igw_statuses.txt'}
    "IPSEC"     {reportStatuses 'ipsec_statuses.txt'}
    "KBC"       {reportStatuses 'kbcluster_statuses.txt'}
    "KBNODES"   {reportStatuses 'kbnode_statuses.txt'}
    "NGW"       {reportStatuses 'natgw_statuses.txt'}
    "SUBNET"    {reportStatuses 'subnet_statuses.txt'}
    "VCN"       {reportStatuses 'vcn_statuses.txt'}
    default {
        Write-Output "Invalid option $options"
        Write-Output "Valid options are:"
        Write-Output ""
        Write-Output "VCN SUBNET IGW IPSEC NGW DRG VM DBAAS DBNODE KBC KBNODES FSERVICE A10 BACKUP"
        exit(9)
    }
}
