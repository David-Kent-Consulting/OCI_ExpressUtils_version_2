#!/usr/local/bin/pwsh
# snapbackup_swake.ps1

param(
    [parameter(Mandatory=$true)]
        [string]$inputFile,
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

########################################################################################
### This program calls the programs $backupBootVol and $backupBlockVol, which results ##
### in boot and block volume snap backups replicating from $sourceRegion to         ####
### $targetRegion. It begins by reading from the input file $inputFile, then        ####
### converts the JSON to a dictionary object. The object is walked down and read,   ####
### with values passed to functions and CMDLETS as appropiate. The program will ABEND ##
### on an error, but otherwise runs perpetually. Jobs called by Start-Threadjob     ####
### are properly housekeeped to ensure memory leaks do not ocurr.                   ####
########################################################################################

$Path           = "/Users/henrywojteczko/Documents/GitHub/NWMSU/master/test"
Set-Location    $Path
$backupBootVol  = $Path + "/BackupBootVolumes.ps1"
$backupBlockVol = $Path + "/BackupBlockVolumes.ps1"
$input          = Get-Content -Path ($Path + "/" + $inputFile) | ConvertFrom-Json -AsHashtable
$lockFile       = "/tmp/snapbackup_swake.LCK"
$runCount       = 0
# $stopCount      = 21
# $interval       = 1800

# foreach ($compartment in $compartments){Write-Output $input.compartments.compartment_name}
# exit

function StartJob(
    [parameter(Mandatory=$true)]
        [string]$program,
    [parameter(Mandatory=$true)]
        [string]$myCompartment,
    [parameter(Mandatory=$true)]
        [string]$mySourceRegion,
    [parameter(Mandatory=$true)]
        [string]$myTargetRegion
){
    if (Test-Path -Path $backupBootVol){
        # The throttle limit default in Powershell is 5 threads. This particular code is very
        # low on CPU consumption. We set the thread limit to 8 to limit the number of concurrent
        # snap job copies to 8 due to inherent limitations in OCI backend infrastructure. An
        # initial uptick in CPU consumption by starting the job is avoided by placing the daemon
        # to sleep for 30 seconds after each invocation.
        return(
            Start-ThreadJob -Name ($myCompartment + "_" + $program + "_JOB") `
                -ThrottleLimit 4 `
                -ArgumentList $myCompartment, $mySourceRegion, $myTargetRegion `
                -FilePath $program
        )
    }
}# end function StartJob(

try{
    if (test-path -Path $lockFile 2> $null){
        $output = "EXCEPTION - $lockFile present, possibly due to this program running."
        Write-Output $output
        Write-Output "Please remove the lock file if this program is not running and restart it."
        exit(1)
    }else{
        $output = "snapback_swake.ps1 started at " + (Get-Date)
        Write-Output $output | Out-File -FilePath $lockFile
    }
    # if ($myProcs.count -ge 1){exit}
    if (Test-Path -Path $Path){
        Write-Output (get-date)
        Write-Output "snapbackup sleep-wake deamon started, This job will perpetually run unless a job ABENDS."
        Write-Output "Running this deamon with the option 'DEBUG' will send detailed output to the console. Otherwise"
        Write-Output "there is no output except on an exception."
        Write-Output ""
        $KEEP_RUNNING = $true
        while ($KEEP_RUNNING){
            foreach ($compartment in $input.compartments){
                # $compartment.compartment_name
                # $compartment.region
                # $compartment.dr_region
                # We tried writing this with the logic below in a function, it did not go well.
                # So unfortunately we have to place the logic for job management and housekeeping
                # here in the main body. We'll fix this when we port the codebase to Python3.
                $job = Get-Job -Name ($compartment.compartment_name + "_" + $backupBootVol + "_JOB") 2> $null
                if ($null -eq $job){
                    $bootBackupJob = StartJob $backupBootVol $compartment.compartment_name $compartment.region $compartment.dr_region
                    if ($option.ToUpper() -eq "DEBUG"){
                        Write-Output (Get-Date)
                        Write-Output $bootBackupJob
                    }
                    Remove-Variable bootBackupJob
                }elseif ($job.State -eq "Completed") {
                    if ($option.ToUpper() -eq "DEBUG"){
                        Write-Output (Get-Date)
                        Write-Output $job
                        Receive-Job -Id $job.id
                    }elseif ($job.state -eq "Failed"){
                        Write-Output (Get-Date)
                        Write-Output "EXCEPTION - The job has failed. Daemon snapbackup_swake."
                        $job
                        Receive-Job -Id $job.id
                        $KEEP_RUNNING = $false
                    }
                    Remove-Job -Id $job.id
                    Remove-Variable job
                }
                $job = get-job -name ($compartment.compartment_name + "_" + $backupBlockVol + "_JOB") 2> $null
                if ($null -eq $job){
                    $blockBackupJob = StartJob $backupBlockVol $compartment.compartment_name $compartment.region $compartment.dr_region
                    if ($option.ToUpper() -eq "DEBUG"){
                        Write-Output (Get-Date)
                        Write-Output $blockBackupJob
                    }
                    Remove-Variable blockBackupJob
                }elseif ($job.State -eq "Completed"){
                    if ($option.ToUpper() -eq "DEBUG"){
                        Write-Output (Get-Date)
                        Write-Output $job
                        Receive-Job -Id $job.id
                    }elseif ($job.State -eq "Failed") {
                        Write-Output (Get-Date)
                        Write-Output "EXCEPTION - The job has failed. Daemon snapbackup_swake."
                        $job
                        Receive-Job -Id $job.id
                        $KEEP_RUNNING = $false
                    }
                    Remove-Job -Id $job.id
                    Remove-Variable job
                }
                Start-Sleep -Seconds 30
            }
            Start-Sleep -Seconds $interval
            $runCount = $runCount + 1
            if ($runCount -eq $stopCount){
                if ($KEEP_RUNNING){
                    Remove-Item -Path $lockFile
                    $KEEP_RUNNING = $false
                }
            }else{
                $output = "This program will stop in " + ($stopCount - $runCount) + " cycles. It should be started by an entry in the ansible user's cron file."
                Write-Output (Get-Date)
                Write-Output $output
            }
            
        }# end foreach ($compartment in $compartments){
    } else {
        $output = "EXCEPTION - $Path not found. Program ABEND."
        Write-Output $output
        exit(1)
    }
}
finally{
    Write-Output (Get-Date)
    Write-Output "snapbackup sleep-wake daemon halted"
}