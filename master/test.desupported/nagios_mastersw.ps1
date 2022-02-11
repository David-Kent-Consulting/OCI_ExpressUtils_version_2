#!/usr/local/bin/pwsh
# nagios_mastersw.ps1

param(
    [parameter(Mandatory=$true)]
        [int]$interval,
    [parameter(Mandatory=$true)]
        [int]$stopCount,
    [parameter(Mandatory=$false)]
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

$Path       = "/Users/henrywojteczko/Documents/GitHub/NWMSU/master/test"
$SWP        = $Path + '/nagios_swake.ps1'
$JobList    = "BACKUP", "DATABASE", "DRG", "IGW", "IPT", "KBC", "NFS", "NGW", "SUBNET", "VCN"
$lockFile   = "/tmp/nagios_swake.LCK"
$runCount   = 0

Set-Location $Path

function StartJob(
    [parameter(Mandatory=$true)]
        [string]$myJob,
    [parameter(Mandatory=$true)]
        [string]$ProgramToRun
){
    if (Test-Path -Path $ProgramToRun){
        # The throttle limit default in Powershell is 5 threads. In this code, we reduce the number of
        # threads to 4. In this case, the number of PROCs on the Oracle VM should be a shape of
        # VM.Standard2.4. The shape must be increased to VM.Standard2.8 if the number of threads are
        # increased beyond 4.
        return(Start-ThreadJob -Name ($myJob + '_JOB') `
            -ThrottleLimit 4 `
            -ArgumentList $myJob `
            -FilePath $ProgramToRun)
    } else {
        return($null)
    }
}

$KEEP_RUNNING = $true
Write-Output (Get-Date)
Write-Output "Starting Nagios Sleep-Wake Processes."
Write-Output "Running this deamon with the option 'DEBUG' will send detailed output to the console. Otherwise"
Write-Output "there is no output except on an exception."
Write-Output ""
if (Test-Path -Path $lockFile){
    Write-Output "EXCEPTION! - Lock file $lockFile present. Make sure nagios_mastersw.ps1 may be running."
    Write-Output "Check for it, and if it is not running, remove this file and try again."
    exit(1)
}else{
   Get-Date | Out-File $lockFile
   $output = "Starting the Nagios Sleep-Wake Processes." 
    Write-Output $output | Out-File -FilePath $lockFile -Append
}

while ($KEEP_RUNNING){
    $output = "There are " + ($stopCount - $runCount) + " runs  of $interval seconds each remaining for this sleep-wake daemon as of " + (get-date)
    Write-Output $output | Out-File -FilePath $lockFile -Append
    foreach ($Job in $JobList){
        Remove-Variable myJob 2> $null
        $myJob = Get-Job -Name ($Job + '_JOB') 2> $null
        if ($null -eq $myJob){
            if ($null -eq ($myJob = StartJob $Job $SWP)){
                Get-Date
                Write-Output "EXCEPTION - $SWP could not run with option $Job"
                $KEEP_RUNNING = $false
            }elseif ($option.ToUpper() -eq "DEBUG") {
                $myJob
            }
        } else {
            if ($myJob.State -eq "Completed"){
                if ($option.ToUpper() -eq "DEBUG"){
                    Get-Date
                    Write-Output $myJob
                    Receive-Job -Id $myJob.Id
                }
                Remove-Job -Id $myJob.Id
            }elseif ($myJob.State -eq 'Failed') {
                $output = "EXCEPTION - Job " + $myJob.Name + " with the job ID of " +$myJob.id + "Failed"
                Get-Date
                Write-Output $output
                if ($option.ToUpper() -eq "DEBUG"){
                    Get-Date
                    Write-Output $myJob
                    Receive-Job -Id $myJob.Id
                }
                $KEEP_RUNNING = $false
            }
        }
    }
    Start-Sleep -Seconds $interval
    if ($runCount -eq $stopCount){
        $KEEP_RUNNING = $false
        Remove-Item -Path $lockFile
    }else{
        $runCount = $runCount +1
    }
}





