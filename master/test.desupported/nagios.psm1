# File nagios.psm1

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

function CheckBackups(
    [parameter(Mandatory=$true)]
        [array]$myCompartmentsToCheck,
    [parameter(Mandatory=$true)]
        [string]$myPath
){
    $TEMP_PATH = $myPath + '/logs/nagios_plugin_backup_temp.txt'
    ################### ################### ################### ################### ###################
    ###         THIS CODE IS CURRENTLY BEING REFACTORED - GATHERING OF VM, VM VOL, AND VM ATTACHMENT ##
    ###         OBJECTS TO BE MOVED OUTSIDE OF THIS CODE BLOCK AND TO BE PASSED AS DICTIONARY OBJECTS##
    ###         AT START OF THE SW PROC, SIMILAR TO WHAT IS BEING DONE WITH VCNS AND COMPARTMENTS.
    ###         THE EFFICIENCY OF THE LOOP ITERATIONS IS ALSO BE BE IMPROVED.
    ################### ################### ################### ################### ###################

    # $myCompartmentsToCheck should be an array of strings consisting of
    #   compartment_name    - string representing the name of a comparment to search for
    #   region              - string representing the primary region where backups are stored
    #   dr_region           - string representing the destination region where backups have been copied to
    $ERROR_STATE=$false
    Write-Output "" | Out-File -FilePath $TEMP_PATH
    $bootVolbackupObjects       = @{}   # store all boot vol backup items for primary region
    $drBootVolbackupObjects     = @{}   # store all boot vol backup items for the DR region
    $blockVolbackupObjects      = @{}   # store all block vol backup items for primary region
    $drBlockVolbackupObjects    = @{}  # store all block vol backup items for the DR region
    # we start by getting all the backups by VM for each compartment, and store the data into
    # the above dictionary objects. Our output for the nagios plugin for backups will be
    # constructed from the data in these objects.
    Write-Output "Starting data collection of all backup objects for selected compartments and regions......"
    foreach ($item in $myCompartmentsToCheck){
        # $item
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            # $compartment
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        $compartment_name = $myCompartment.name
        $VMs = $vmObjects.$compartment_name.keys
        foreach ($myVmName in $VMs){
            Write-Output "Collecting backup data for VM $myVmName......"
            $myVmBootVolBackups = oci bv boot-volume-backup list `
                --compartment-id $myCompartment.id `
                --boot-volume-id $vmObjects.$compartment_name.$myVmName.bootvolAttachment.'boot-volume-id' `
                --region $item.region `
                --all `
                | ConvertFrom-Json -AsHashtable
            $bootVolbackupObjects.add($myVmName, $myVmBootVolBackups)
            $myDrBootVolBackups = oci bv boot-volume-backup list `
                --compartment-id $myCompartment.id `
                --boot-volume-id $vmObjects.$compartment_name.$myVmName.bootvolAttachment.'boot-volume-id' `
                --region $item.dr_region `
                --all `
                | ConvertFrom-Json -AsHashtable
            $drBootVolbackupObjects.add($myVmName, $myDrBootVolBackups)
            if ($null -ne $vmObjects.$compartment_name.$myVmName.blockvolAttachment){
                # Write-Output "block vol found"
                $myBlockVolBackups = oci bv backup list `
                    --compartment-id $myCompartment.id `
                    --volume-id $vmObjects.$compartment_name.$myVmName.blockvolAttachment.'volume-id' `
                    --region $item.region `
                    --all `
                    | ConvertFrom-Json -AsHashtable
                $blockVolbackupObjects.Add($myVmName, $myBlockVolBackups)
                $myDrBlockVolBackups = oci bv backup list `
                    --compartment-id $myCompartment.id `
                    --volume-id $vmObjects.$compartment_name.$myVmName.blockvolAttachment.'volume-id' `
                    --region $item.dr_region `
                    --all `
                    | ConvertFrom-Json -AsHashtable
                $drBlockVolbackupObjects.add($myVmName, $myDrBlockVolBackups)
            }# end if ($null -ne $vmObjects.$compartment_name.$myVmName.blockvolAttachment){
        }# end foreach ($myVmName in $VMs){
    } # end foreach ($item in $myCompartmentsToCheck){
    # $bootVolbackupObjects
    # $drBootVolbackupObjects
    # $blockVolbackupObjects
    # $drBlockVolbackupObjects

    Write-Output ""
    Write-Output "Creating Nagios report files for plugin......"
#     # We have to start over with getting compartment objects, and subsequently all VM objects.
#     # This will enable us to search the dictionary objects, whose key names are tied to each
#     # VM display-name.
    foreach ($item in $myCompartmentsToCheck){
        $compartment_name = $item.compartment_name
        # Write-Output $compartment_name
        # $vmObjects
        $VMs = $vmObjects.$compartment_name.keys
        foreach ($myVmName in $VMs){
            # $myVmName
            $bootVolBackupCount = 0
            $drBootVolBackupCount = 0
            $blockVolBackupCount = 0
            $drBlockVolBackupCount = 0
            foreach ($vol in $bootVolbackupObjects.$myVmName.data){
                if ($vol.'lifecycle-state' -eq 'AVAILABLE'){$bootVolBackupCount = $bootVolBackupCount +1}
            }
            foreach ($vol in $drBootVolbackupObjects.$myVmName.data){
                if ($vol.'lifecycle-state' -eq 'AVAILABLE'){$drBootVolBackupCount = $drBootVolBackupCount +1}
            }
            foreach ($vol in $blockVolbackupObjects.$myVmName.data){
                if ($vol.'lifecycle-state' -eq 'AVAILABLE'){$blockVolBackupCount = $blockVolBackupCount +1}
            }
            foreach ($vol in $drBlockVolbackupObjects.$myVmName.data){
                if ($vol.'lifecycle-state' -eq 'AVAILABLE'){$drBlockVolBackupCount = $drBlockVolBackupCount +1}
            }
            # this sets $ERROR_STATE to $true if boot vol or block vol copies do not match between regions
            if ($bootVolBackupCount -ne $drBootVolBackupCount -or $blockVolBackupCount -ne $drBlockVolBackupCount -or $bootVolBackupCount -eq 0){
                $ERROR_STATE = $true
            }
            # here we must set the 1st line of the file to OK or WARNING for the plugin script to function as defined
            if ($ERROR_STATE){
                Write-Output "WARNING" | Out-File -FilePath $TEMP_PATH
            } else {
                Write-Output "OK" | Out-File -FilePath $TEMP_PATH
            }
            $output = "Backup report for Virtual Machine " + $myVmName 
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            $output = "Boot Volume Copies"
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "STATUS..........BACKUP JOB NAME UTC Time........................VM............SIZE IN GB...................REGION"  | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "=======================================================================================================================" | Out-File -FilePath $TEMP_PATH -Append
            # right here I am over writing $item, need to fix
            foreach ($vol in $bootVolbackupObjects.$myVmName.data){
                if ($vol."lifecycle-state" -ne 'TERMINATED'){
                    $output = $vol.'lifecycle-state' + "  -  " + `
                        $vol.'display-name' + "  -  " + `
                        $vol.type + "  -  " + `
                        $vol.'unique-size-in-gbs' + "          " +`
                        $myCompartment.region
                    Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                }
            }
            # now print block vol copies only if present
            if ($blockVolBackupCount -ne 0){
                Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
                $output = "Block Volume Copies"
                Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                Write-Output "STATUS..........BACKUP JOB NAME UTC Time........................VM............SIZE IN GB...................REGION"  | Out-File -FilePath $TEMP_PATH -Append
                Write-Output "=======================================================================================================================" | Out-File -FilePath $TEMP_PATH -Append
                foreach ($vol in $blockVolbackupObjects.$myVmName.data){
                    if ($vol."lifecycle-state" -eq 'AVAILABLE'){
                        $output = $vol.'lifecycle-state' + "  -  " + `
                            $vol.'display-name' + "  -  " + `
                            $vol.type + "  -  " + `
                            $vol.'unique-size-in-gbs' + "          " +`
                            $myCompartment.region
                        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                    }
                }
            }
            Write-Output "" | Out-File $TEMP_PATH -Append

            if ($ERROR_STATE){
                # The following 2 codeblocks look for volumes found in the primary region that are also found
                # in the secondary region but are not in a consistent lifecycle state. Volumes found in this
                # state are reported. What we are looking for are 2 conditions, volumes stuck in a creating state
                # and volumes that are not properly terminating. This type of issue has been seen in OCI when
                # issues arise on the Oracle backend for volume backup copies between regions. The only fix
                # when this issues are detected is to contact Oracle Support.
                $ITEM_FOUND = $false
                foreach ($vol in $bootVolbackupObjects.$myVmName.data){
                    if ($vol.'lifecycle-state' -ne 'TERMINATED'){
                        foreach ($drItem in $drBootVolbackupObjects.$myVmName.data){
                            if ($vol.'display-name'.Contains($drItem.'display-name')){
                                #Write-Output "Item found"
                                if ($drItem.'lifecycle-state' -ne 'AVAILABLE'){
                                    #Write-Output "But item is not in available state"
                                    $output = $vol.'display-name' + " lifecycle state is AVAILABLE in its primary region, but is in a " `
                                        + $drItem.'lifecycle-state' + " lifecycle state in the DR region."
                                    Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                                    $output = "OCID in the primary region is " + $vol.id
                                    Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                                    $output = "OCID in the DR region is " + $drItem.id
                                    Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                                    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
                                }
                            }
                        }
                    }
                }# end foreach ($vol in $bootVolbackupObjects.$myVmName.data){
                if ($drBootVolBackupCount -ne 0){
                    # Write-Output "we have to now look at block volumes"
                    foreach ($vol in $blockVolbackupObjects.$myVmName.data){
                        # $item
                        if ($vol.'lifecycle-state' -ne 'TERMINATED'){
                            foreach ($drItem in $drBlockVolbackupObjects.$myVmName.data){
                                # $item.'display-name'.Contains($drItem.'display-name')
                                if ($vol.'display-name'.Contains($drItem.'display-name')){
                                    if ($drItem.'lifecycle-state' -ne 'AVAILABLE'){
                                        $output = $vol.'display-name' + " lifecycle state is AVAILABLE in its primary region, but is in a " `
                                            + $drItem.'lifecycle-state' + " lifecycle state in the DR region."
                                        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                                        $output = "OCID in the primary region is " + $vol.id
                                        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                                        $output = "OCID in the DR region is " + $drItem.id
                                        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                                    }
                                }
                            }
                        }
                    }
                }# end if ($drBootVolBackupCount -ne 0){
                
                $output = "There are " + ($bootVolBackupCount + $blockVolBackupCount) + " backup volumes in the primary region " + $item.region + " for VM " + $myVmName
                Write-Output $output | Out-File $TEMP_PATH -Append
                $output = "but there are " + ($drBootVolBackupCount + $drBlockVolBackupCount) + " backup volumes in the DR region " + $item.dr_region
                Write-Output $output | Out-File $TEMP_PATH -Append

                if ($drBootVolBackupCount -ne 0){
                    Write-Output "Here are the boot volumes found in the DR region for this VM......" | Out-File -FilePath $TEMP_PATH -Append
                    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
                    foreach ($vol in $drBootVolbackupObjects.$myVmName.data){
                        if ($vol.'lifecycle-state' -eq 'AVAILABLE'){
                            $output = $vol.'display-name'
                            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                        }
                    }
                    if ($blockVolBackupCount -ne 0){
                        Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
                        Write-Output "And here are the block volume copies found in the DR region for this VM......" | Out-File -FilePath $TEMP_PATH -Append
                        foreach ($vol in $drBlockVolbackupObjects.$myVmName.data){
                            if ($vol."lifecycle-state" -ne 'TERMINATED'){
                                $output = $vol.'display-name'
                                Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                            }
                        }
                    }
                }# end if ($drBootVolBackupCount -ne 0){
            } else {
                $output = "There are " + ($bootVolBackupCount + $blockVolBackupCount) + " backup volumes in both regions and there are no errors for VM " + $myVmName
                Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            }# end if ($ERROR_STATE){
            $outFile = $Path + '/logs/backups_statuses_' + $myVmName + '.txt'
            Copy-Item -Path $TEMP_PATH -Destination $outFile
            Remove-Item -Path $TEMP_PATH
            $ERROR_STATE = $false
        }# end foreach ($myVmName in $VMs){
    }# end foreach ($item in $myCompartmentsToCheck){

#     # This section will dynamically build the nagios import configuration files. We begin as before
#     # by running through each compartment, building a list of VMs in the compartment, and then
#     # write out the config files. These files should be copied to /usr/local/nagions/etc/import
#     # and then imported en mass under either of 2 conditions: 1) When a VM is added to backups, or
#     # 2) when a code upgrade is performed on Nagios. Note removal of VMs from Nagios monitoring
#     # must be performed manually by 1) removing the stanzas from /usr/local/etc/commands.cfg and
#     # /usr/local/nagios/hosts/localhost.cfg, and then by removing any staged Nagios config files that
#     # are staged in /usr/local/nagios/etc/import. Please see the link below for instructions from Nagios.
#     # https://assets.nagios.com/downloads/nagiosxi/docs/Importing-Core-Configuration-Files-Into-Nagios-XI.pdf 
#     # start by removing all files ending in .cfg from the logs directory
    Write-Output "Building the Nagios plugin import configuration files......"
    $TEMP_PATH = $Path + '/logs/OciBackup*.cfg'
    Remove-Item -Path $TEMP_PATH
    Remove-Variable $TEMP_PATH
#     # start walking down the compartments
    foreach ($item in $myCompartmentsToCheck){
        # $item
        $compartment_name = $item.compartment_name
        # Write-Output $compartment_name
        # $vmObjects
        $VMs = $vmObjects.$compartment_name.keys
        # $VMs
        foreach ($myVmName in $VMs){
            # $myVmName
            $TEMP_PATH = $Path + '/logs/OciBackup_' + $myVmName + 'commands.cfg'
            $output = '# Nagios import configuration file ' + $TEMP_PATH
            Write-Output $output | Out-File -FilePath $TEMP_PATH
            Write-Output '# Created by DKC Nagios Plugin nagios_swake.ps1' | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "# Copy to /usr/local/nagios/import and then import into Nagios to add service monitor" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
            $output = "define command{"
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            $output = "        command_name check_backup_" + $myVmName + "_oci"
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
             # We have to make sure the $ is not interpreted by Powershell during the string concatenation
            $output = "        command_line " + "$" +"USER1" + "$" + "/nagios_plugin.ps1 BACKUP backups_statuses_" + $myVmName + ".txt"
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "}" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "# end of file" | Out-File -FilePath $TEMP_PATH -Append
             # now, create the service configuration file
            $TEMP_PATH = $Path + '/logs/OciBackup_' + $myVmName + 'service.cfg'
            $output = '# Nagios import configuration file ' + $TEMP_PATH
            Write-Output $output | Out-File -FilePath $TEMP_PATH
            Write-Output '# Created by DKC Nagios Plugin nagios_swake.ps1' | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "# Copy to /usr/local/nagios/import and then import into Nagios to add service monitor" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "define service{" | Out-File -FilePath $TEMP_PATH -Append
             # the code below assumes the services are being added to the Nagios localhost node
             # The code would have to be tweaked if running on a node other than localhost or from
             # an HTTP engine, just as JS.Server
            Write-Output "    use                    local-service" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "    host_name              localhost" | Out-File -FilePath $TEMP_PATH -Append
            $output =    "    service_description    OCI Backup Status For VM " + $myVmName
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            $output =    "    check_command          check_backup_" + $myVmName +"_oci"
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "}" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
            Write-Output "# end of file" | Out-File -FilePath $TEMP_PATH -Append
        }


    } # end foreach ($myCompartment in $myCompartmentsToCheck){
}# end function CheckBackups

function CheckDbNodes(
    [parameter(Mandatory=$true)]
    [string]$myPath
){
    # This function reports on the up status of DBaaS service nodes health within the specified
    # region and compartment. To do this, the function must:
    # 1)    Get the compartments
    # 2)    Get all the DB systems that are not terminated
    # 3)    Get all the DB nodes per DB system that are not terminated
    # 4)    Check the up status of each DB node
    # 5)    Prepare the Nagios report and configuration plugin files
    $TEMP_PATH = $myPath + '/logs/nagios_plugin_database_temp.txt'
    foreach ($item in $myChecks.dbsystems){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        $myDbSystems   = GetDbSystems $myCompartment $item.dbsystem_name $item.region
        # $myDbSystems.data
        foreach ($myDbSystem in $myDbSystems.data){
            if ($myDbSystem.'lifecycle-state' -ne 'TERMINATED'){
                # $myDbSystem
                # the following gets every DB node within the availability domain, it's how the AIP works.
                # We have to fall out into a different loop below to extract just the DB node we are
                # looking for. The API doc incorrectly states that the db-system-id is not required.
                # Thus we have to make an iterative search through a list recursively for each DBaaS
                # in order to hammer down on the specific DB Node we are searching for. The -all option
                # is essential to ensure the API returns all data in 1 call.
                $myDbNodes = oci db node list `
                    --compartment-id $myCompartment.id `
                    --db-system-id $myDbSystem.id `
                    --all `
                    --region $item.region `
                    | ConvertFrom-Json -AsHashtable
                #$myDbNodes.data
                foreach ($myDbNode in $myDbNodes.data){
                    if ($myDbSystem.id -eq $myDbNode.'db-system-id' -and $myDbNode.'lifecycle-state' -ne 'TERMINATED'){
                        $DBNODE_FILE_PATH = $Path + '/logs/dbnode_statuses_' + $myDbNode.hostname + '.txt'
                        # $DBNODE_FILE_PATH
                        # Get the IP address of the DB Node
                        $myVnic = oci network vnic get `
                            --vnic-id $myDbNode.'vnic-id' `
                            | ConvertFrom-Json -AsHashtable
                        $myIpAddress = $myVnic.data.'private-ip'
                        #$myIpAddress
                        #$myIpAddress = $myVnic.data.
                        # Now we create Nagios report and configuration plugin files for each DB node that is discovered
                        # start by checking to see if the lifecycle-state is not AVAILABLE, if so, set status to CRITICAL
                        # end report file, otherwise set status to OK.
                        if ($myDbNode.'lifecycle-state' -ne 'AVAILABLE'){
                            # $myDbSystem.'display-name'
                            # $myDbNode.hostname
                            # $myDbNode.'lifecycle-state'
                            Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH
                            
                        } else {
                            # $myDbSystem.'display-name'
                            # $myDbNode.hostname
                            # $myDbNode.'lifecycle-state'
                            Write-Output "OK" | Out-File -FilePath $TEMP_PATH
                        }
                        # Now continue to build the report file
                        $output =  "DB NODE STATUS REPORT ON DB SYSTEM " + $myDbSystem.'display-name' + " ON SERVICE NODE " + $myDbNode.hostname 
                        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                        Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
                        Write-Output "DB SYSTEM____SERVICE NODE____IP ADDRESS____STATUS" | Out-File -FilePath $TEMP_PATH -Append
                        Write-Output "========================================================" | Out-File -FilePath $TEMP_PATH -Append
                        $output = $myDbSystem.'display-name' + '       ' + $myDbNode.hostname + '      ' + $myIpAddress + '   ' + $myDbNode.'lifecycle-state'
                        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
                        Copy-Item $TEMP_PATH -Destination $DBNODE_FILE_PATH
                        Remove-Item -Path $TEMP_PATH
                        #create the nagios configuration files
                        # we cannot use CreateNagiosConfigurationFiles due to an unknown issue, adn have written the code to manage creating the files
                        # here
                        $outFile = $Path + "/logs/OciDbNode_" + $myDbNode.hostname + "_commands.cfg"
                        $output = "# Nagios configuration file " + $outFile
                        Write-Output $output | Out-File -FilePath $outFile
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "# Created by DKC Nagios Plugin nagios_swake.ps1" | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "# Copy to /usr/local/nagios/import and then import into Nagios to add service monitor" | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "define command{" | Out-File -FilePath $outFile -Append
                        $output = "    " + "command_name check_dbnode_" + $myDbNode.hostname | Out-File -FilePath $outFile -Append
                        Write-Output $output | Out-File -FilePath $outFile -Append
                        $output = "    " + "command_line " + "$" +"USER1" + "$" + "/nagios_plugin.ps1 DBNODE " + 'dbnode_statuses_' + $myDbNode.hostname + '.txt' | Out-File -FilePath $outFile -Append
                        Write-Output $output | Out-File -FilePath $outFile -Append
                        Write-Output "}" | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "# end of file" | Out-File -FilePath $outFile -Append
                        $outfile = $Path + "/logs/OciDbNode_" + $myDbNode.hostname + "_service.cfg"
                        $output = "Nagios configuration file " + $outfile | Out-File -FilePath $outFile
                        Write-Output $output | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "# Created by DKC Nagios Plugin nagios_swake.ps1" | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "# Copy to /usr/local/nagios/import and then import into Nagios to add service monitor" | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "define service{" | Out-File -FilePath $outFile -Append
                        Write-Output "    use                    local-service" | Out-File -FilePath $outFile -Append
                        Write-Output "    host_name              localhost" | Out-File -FilePath $outFile -Append
                        $output = "    service_description    OCI DB Node Status for " + $myDbNode.hostname | Out-File -FilePath $outFile -Append
                        Write-Output $output | Out-File -FilePath $outFile -Append
                        $output = "    check_command          check_dbnode_" + $myDbNode.hostname | Out-File -FilePath $outFile -Append
                        Write-Output $output | Out-File -FilePath $outFile -Append
                        Write-Output "}" | Out-File -FilePath $outFile -Append
                        Write-Output "" | Out-File -FilePath $outFile -Append
                        Write-Output "# end of file" | Out-File -FilePath $outFile -Append
                    }# end if ($myDbNode.'lifecycle-state' -ne 'AVAILABLE'){
                }# end if ($myDbSystem.id -eq $myDbNode.'db-system-id' -and $myDbNode.'lifecycle-state' -ne 'TERMINATED'){
            }# end foreach ($myDbNode in $myDbNodes.data){
        }# end foreach ($myDbSystem in $myDbSystems.data){
    }# end foreach ($item in $myChecks.dbsystems){
}# end function CheckDbNodes
function CheckDbSystems(
    [parameter(Mandatory=$true)]
    [string]$myPath
)
{
    $TEMP_PATH = $myPath + '/logs/nagios_plugin_database_temp.txt'
    $DBAAS_FILE_PATH    = $myPath + '/logs/dbsystems_statuses.txt'
    $ERROR_STATE = $false
    $cntr=0
    $dbSystemObjects = @{}   # our dict object
    foreach ($item in $myChecks.dbsystems){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        $myDbSystems   = GetDbSystems $myCompartment $item.dbsystem_name $item.region
        foreach ($myDbSystem in $myDbSystems.data){
            $record = SelectDbSystem $myDbSystem.'display-name' $myDbSystems
            $dbSystemObjects.add($cntr, $record)    # a pure PIA, only way to get entire object to properly append to the dict. object, we
                                                    # do not want it to add as a bunch of lines of type string.
            if ($record.'lifecycle-state' -ne 'AVAILABLE'){
                $ERROR_STATE = $true
            }
            $cntr=$cntr+1
        }
    }
    if ($ERROR_STATE){
        Write-Output "Critical" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }

    $count = 0
    while ($count -le $cntr-1){
        $output = $dbSystemObjects.$count.'display-name' + "        " + $dbSystemObjects.$count.'lifecycle-state'
        $count = $count + 1
        Write-Output $output | Out-File $TEMP_PATH -Append
    }
    Copy-Item $TEMP_PATH -Destination $DBAAS_FILE_PATH
    Remove-Item -Path $TEMP_PATH
    # Create the Nagios configuration files
    $NagiosConfigurationFile.command_file           = "ociDbaaS_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_dbsystems_oci"
    $NagiosConfigurationFile.command_line           = "command_line " + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 DBAAS"
    $NagiosConfigurationFile.service_file           = "ociDbaaS_service.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI DBAAS Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_dbsystems_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
} # end function CheckDbSystems

function CheckDRGs(
    [parameter(Mandatory=$true)]
    [string]$myPath
)
{
    $ERROR_STATE = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin__drg_temp.txt'
    $DRG_FILE_PATH      = $myPath + '/logs/drg_statuses.txt'
    $drgObjects  = @{}
    $drgCount = 0
    foreach ($item in $myChecks.networks){
        if ($null -ne $item.drg_name){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
            $myVcns = GetVcn $myCompartment $item.region
            $myVcn  = SelectVCN $item.vcn_name $myVcns
            if ($null -ne $myVcn){
                if ($myVcn -ne 'TERMINATED'){
                    $myDRGs = GetDRGs $myVcn $item.region
                    $myDRG = SelectDRG $myDRGs $item.drg_name
                    # the method SelectDRG will not select a terminated object, so we don't have to check for that condition
                    if ($null -ne $myDRG){
                        $drgObjects.Add($drgCount, $myDRG)
                        $drgCount = $drgCount + 1
                        if ($myDRG.'lifecycle-state' -ne 'AVAILABLE'){$ERROR_STATE = $true}
                    }
                }
            } else {
                # check the other region for the DRG, starting by selecting the VCN in the DR region
                $myVcns = GetVCN $myCompartment $item.dr_region
                $myVcn  = SelectVCN $item.vcn_name $myVcns
                if ($null -ne $myVcn){
                    $myDRGs = GetDRGs $myVcn $item.dr_region
                    $myDRG  = SelectDRG $myDRGs $item.drg_name
                    $drgObjects.Add($drgCount, $myDRG)
                    $drgCount = $drgCount + 1
                    if ($myDRG.'lifecycle-state' -ne 'AVAILABLE'){$ERROR_STATE = $true}
                }
            }
        }# end if ($null -ne $item.drg_name){
    }# end foreach ($item in $myChecks.networks){
    if ($ERROR_STATE){
        Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    $count = 0
    while ($count -le $drgCount){
        $output = $drgObjects.$count.'display-name' + "        " + $drgObjects.$count.'lifecycle-state'
        Write-Output $output | Out-File $TEMP_PATH -Append
        $count = $count +1
    }
    Copy-Item $TEMP_PATH -Destination $DRG_FILE_PATH 
    Remove-Item -Path $TEMP_PATH
    # Create the Nagios configuration files
    $NagiosConfigurationFile.command_file           = "ociDrg_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_drg_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 DRG"
    $NagiosConfigurationFile.service_file           = "ociDrg_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI DRG Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_drg_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}# end function CheckDRGs

function CheckIGWs(
    [parameter(Mandatory=$true)]
    [string]$myPath
){
    $ERROR_STATE = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin__igw_temp.txt'
    $IGW_FILE_PATH      = $myPath + '/logs/igw_statuses.txt'
    $igwObjects  = @{}
    $igwCount    = 0
    foreach($item in $myChecks.networks){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        # Checking for the VCN is not required, but desirable since the DRG must
        # be bound to a VCN. This is a convenient bit of code that will check the primary
        # region, and then the DR region if the VCN is not found in the primary region.
        if ($null -ne $item.igw_name){
            $myVcns = GetVcn $myCompartment $item.region
            $myVcn  = SelectVCN $item.vcn_name $myVcns
            if ($null -ne $myVcn){
                if ($myVcn.'lifecycle-state' -ne 'TERMINATED'){
                    $myIGWs = GetIGWs $myVcn $item.region
                    $myIGW = SelectIGW $item.igw_name $myIGWs
                    if ($myIGW.'lifecycle-state' -ne 'TERMINATED'){
                        $igwObjects.Add($igwCount, $myIGW)
                        $igwCount = $igwCount + 1
                        if ($myIGW.'lifecycle-state' -ne 'AVAILABLE'`
                            -and $myIGW.'is-enabled' -ne $true){
                            $ERROR_STATE = $true
                        }
                    }
                }
            }else {
                Write-Output "VNC not found, write code here to check other region with DR project"
            }
        }
    }# end foreach($item in $myChecks.networks){
    # create the Nagios report and configuration files
    if ($ERROR_STATE){
        Write-Output "WARNING" | Out-File -FilePath $TEMP_PATH
    }else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    Write-Output "IGW REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "IGW Gateway Name____Enabled____Status" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "==========================================" | Out-File -FilePath $TEMP_PATH -Append
    $count = 0
    while ($count -le $igwCount){
        $output = $myIGW.'display-name' + '    ' + `
            $myIGW.'is-enabled' + '    ' + `
            $myIGW.'lifecycle-state'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count + 1
    }
    Copy-Item $TEMP_PATH -Destination $IGW_FILE_PATH
    Remove-Item -Path $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociIgw_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_igw_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 IGW"
    $NagiosConfigurationFile.service_file           = "ociIgw_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI IGW Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_igw_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}# end function CheckIGWs

function CheckIpTunnels(
    [parameter(Mandatory=$true)]
    [string]$myPath
)
{
    $ERROR_STATE  = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin_ipt_temp.txt'
    $IPSEC_FILE_PATH    = $myPath + '/logs/ipsec_statuses.txt'
    # this function must:
    #   1) Get the VCN in the primary region, and if not in the primary region
    #       search for it in the DR region
    #   2) Get the DRG
    #   3) Get the IPsec tunnel(s). There should be 2, but there may only be 1
    #   4) Get the health state of the tunnels
    #   5) Get metrics
    #   6) prepare a Nagios report file in the required format for both UP/DOWN
    #       status and performance metrics.
    #   7) Prepare the Nagios configuration files
    # Note this release will not include performance metrics in the report file.
    # A subsequent update will provide this data feed into Magios.
    foreach ($item in $myChecks.networks){
        if ($null -ne $item.ipsec_name){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
            # Checking for the VCN is not required, but desirable since the DRG must
            # be bound to a VCN. This is a convenient bit of code that will check the primary
            # region, and then the DR region if the VCN is not found in the primary region.
            $myVcns = GetVcn $myCompartment $item.region
            $myVcn  = SelectVCN $item.vcn_name $myVcns
            if ($null -ne $myVcn){
                # always do this
                if ($myVcn -ne 'TERMINATED'){
                    $ipSecConnections = GetIpSecConnections $myCompartment $item.region
                    $ipSecConnection = SelectIpSecTunnel $ipSecConnections $item.ipsec_name
                    $myIpSecTunnels = GetIpSecTunnels $ipSecConnection
                } else {
                    Write-Output "VCN not found in primary region, check the DR region, will write this portion"
                    Write-Output "after the DR IPsec tunnel is stood up."
                }
            }
        }# end if ($null -ne $item.ipsec_name)
    }# end foreach ($item in $myChecks.networks){
    # now check out the health of each object
    if ($ipSecConnection.'lifecycle-state' -ne 'AVAILABLE'){$ERROR_STATE = $true}
    foreach ($myTunnel in $myIpSecTunnels.data){
        if ($myTunnel.'lifecycle-state' -ne 'AVAILABLE' -or $myTunnel.status -ne 'UP'){$ERROR_STATE = $true}
    }
    # now begin to build the Nagios report file
    if ($ERROR_STATE){
        Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    Write-Output "IPSEC CONNECTION REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Connection Name____Routed Network____CPE IP_____________Status________" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "======================================================================" | Out-File -FilePath $TEMP_PATH -Append
    $output = $ipSecConnection.'display-name' + '        ' + `
        $ipSecConnection.'static-routes' + '        ' + `
        $ipSecConnection.'cpe-local-identifier' + '    ' + `
        $ipSecConnection.'lifecycle-state'
    Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "IPSEC TUNNEL REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Tunnel Name____VPN IP__________CPE IP_____________Status" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "======================================================================" | Out-File -FilePath $TEMP_PATH -Append
    foreach ($myIpSecTunnel in $myIpSecTunnels.data){
        $output = $myIpSecTunnel.'display-name' + '       ' + `
            $myIpSecTunnel.'vpn-ip' + `
                '    ' + $myIpSecTunnel.'cpe-ip' + `
                '    ' + $myIpSecTunnel.status
            Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
    }

    Copy-Item $TEMP_PATH -Destination $IPSEC_FILE_PATH
    Remove-Item -Path $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociIPsec_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_ipsec_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 IPSEC"
    $NagiosConfigurationFile.service_file           = "ociIPsec_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI IPSEC Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_ipsec_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}# end function CheckIpTunnels

function CheckKbCluster(
    [parameter(Mandatory=$true)]
    [string]$myPath
){
    # This function reports on the state of Kubernetes clusters. It must:
    #   1) Get the clusters from t he compartment and select the correct cluster
    #   2) prepare the Nagios plugin report and configuration files
    $ERROR_STATE      = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin_kbc_temp.txt'
    $KBCLUSTER_FILE_PATH= $myPath + '/logs/kbcluster_statuses.txt'
    $kbclusterObjects = @{}
    $kbClusterCount   = 0
    foreach ($item in $myChecks.kubernetes){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        $myKbClusters  = GetKbClusters $myCompartment $item.region
        $myKbCluster = SelectKbCluster $myKbClusters $item.kbcluster_name
        $kbclusterObjects.Add($kbClusterCount, $myKbCluster)
        $kbClusterCount = $kbClusterCount + 1
        if ($myKbCluster.'lifecycle-state' -ne 'ACTIVE'){
            $ERROR_STATE = $true
        }
    }
    # create the Nagios report and configuration files
    if ($ERROR_STATE){
        Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    Write-Output "KUBERNETES CLUSTER REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Cluster Name____Cluster Version____Available Upgrades____State" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "=================================================================" | Out-File -FilePath $TEMP_PATH -Append
    $count = 0
    while ($count -le $kbClusterCount){
        $output = $kbclusterObjects.$count.name + '      ' + `
            $kbclusterObjects.$count.'kubernetes-version' + '            ' + `
            $kbclusterObjects.$count.'available-kubernetes-upgrades' + '               ' + `
            $kbclusterObjects.$count.'lifecycle-state'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count + 1
    }
    Copy-Item $TEMP_PATH -Destination $KBCLUSTER_FILE_PATH
    Remove-Item $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociKbCluster_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_kbc_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 KBC"
    $NagiosConfigurationFile.service_file           = "ociKbCluster_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI KUBENETES CLUSTER Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_kbc_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}# end function CheckKbCluster

function CheckKbNodePools(
    [parameter(Mandatory=$true)]
    [string]$myPath
){
    # This function reports against a list of KB Node pools versus what is discovered.
    # It does this by:
    # 1) Get the KB clusters
    # 2) If the KB cluster is found, then get the all node pools in the compartment
    # 3) Search the nodepools found against the list
    # 4) Set $ERROR_STATUS = $true if there is a missing nodepool
    # 5) Prepare the nagios report and configuration plugin files
    $ERROR_STATUS = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin_kbc_temp.txt'
    $KBNODE_FILE_PATH   = $mypath + '/logs/kbnode_statuses.txt'
    $nodepoolObjects    = @{}
    $nodepoolCount      = 0
    foreach ($item in $myChecks.kubernetes){
        #$item
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        if ($null -ne $item.nodepools){
            $myKbClusters = GetKbClusters $myCompartment $item.region
            #$myKbClusters
            $myKbCluster = SelectKbCluster $myKbClusters $item.kbcluster_name
            #$myKbCluster.name
            if ($myKbCluster.'lifecycle-state' -ne 'TERMINATED'){
                $myKbNodePools = oci ce node-pool list `
                    --compartment-id $myCompartment.id `
                    --region $item.region `
                    --all `
                    | ConvertFrom-Json -AsHashtable
                # $myKbNodePools.data
                foreach ($nodepool_name in $item.nodepools.nodepool_name){
                    $nodepool_found = $false
                    foreach ($myKbNode in $myKbNodePools.data){
                        # $nodepool_name
                        # $myKbNode.name
                        if ($nodepool_name -eq $myKbNode.name){
                            $nodepool_found = $true
                            $nodepoolObjects.Add($nodepoolCount, $myKbNode)
                            $nodepoolCount = $nodepoolCount + 1
                            # $nodepoolObjects
                        }
                    }
                    if ($false -eq $nodepool_found){
                        $ERROR_STATUS = $true
                    }
                    # $ERROR_STATUS
                }# end foreach ($nodepool_name in $item.nodepools.nodepool_name){
            }# end if ($myKbCluster.'lifecycle-state' -ne 'TERMINATED'){
        }# end if ($null -ne $item.nodepools){
    }# end foreach ($item in $myChecks.kubernetes){
    # now create the report file
    if ($ERROR_STATUS){
        Write-Output "WARNING" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    Write-Output "KUBERNETES NODE REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "We expect to find the following nodepools......" | Out-File -FilePath $TEMP_PATH -Append
    foreach ($nodepool_name in $myChecks.kubernetes.nodepools.nodepool_name){
        Write-Output $nodepool_name | Out-File -FilePath $TEMP_PATH -Append
    }
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Here are the node pools that we found......" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "NODEPOOL NAME____STATUS____" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "=================================" | Out-File -FilePath $TEMP_PATH -Append
    $count = 0
    while ($count -le $nodepoolCount-1){
        $output = $nodepoolObjects.$count.name + '    ACTIVE'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count + 1
    }
    Copy-Item -Path $TEMP_PATH -Destination $KBNODE_FILE_PATH
    Remove-Item $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociKbnode_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_kbnode_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 KBNODES"
    $NagiosConfigurationFile.service_file           = "ociKbnode_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI KB Nodes Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_kbnode_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}# end function CheckKbNodePools

function CheckNatGw(
    [parameter(Mandatory=$true)]
    [string]$myPath
){
    $ERROR_STATE  = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin_ngw_temp.txt'
    $NGW_FILE_PATH      = $myPath + '/logs/natgw_statuses.txt'
    $natGwObjects = @{}
    $natGwCount = 0
    # This function must:
    #   1) Get the VCN in the primary region, and if not in the primary region
    #       search for it in the DR region
    #   2) Get the NatGWs, then select from the dictionary list
    #   3) Prepare the Nagios report and configuration files
    foreach ($item in $myChecks.networks){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        if ($null -ne $item.natgw_name){
            $myNatGWs = oci network nat-gateway list `
                --compartment-id $myCompartment.id `
                --region $item.region `
                | ConvertFrom-Json -AsHashtable
            if ($null -ne $myNatGWs){
                # Write-Output "got here"
                $myNatGW = SelectNGW $item.natgw_name $myNatGWs
                if ($null -ne $myNatGW){
                    $natGwObjects.Add($natGwCount, $myNatGW)
                    # $natGwObjects.$natGwCount.'display-name'
                    $natGwCount = $natGwCount + 1
                    if ($myNatGW.'lifecycle-state' -ne 'TERMINATED' -and $myNatGW.'lifecycle-state' -ne 'AVAILABLE'){
                        $ERROR_STATE = $true
                    }
                }
            }
            $myVcns = GetVcn $myCompartment $item.dr_region
            if ($null -ne $myVcns){
                # Write-Output "check DR region"
                $myVcn  = SelectVCN $item.vcn_name $myVcns
                if ($myVcn -ne 'TERMINATED'){
                    $myNatGWs = oci network nat-gateway list `
                        --compartment-id $myCompartment.id `
                        --region $item.dr_region `
                        | ConvertFrom-Json -AsHashtable
                    # $myNatGWs.data
                    $myNatGW = SelectNGW $item.natgw_name $myNatGWs
                    if ($null -ne $myNatGW){
                        $natGwObjects.Add($natGwCount, $myNatGW)
                        # $natGwObjects.$natGwCount.'display-name'
                        $natGwCount = $natGwCount + 1
                        if ($myNatGW.'lifecycle-state' -ne 'TERMINATED' -and $myNatGW.'lifecycle-state' -ne 'AVAILABLE'){
                            $ERROR_STATE = $true
                        }
                    }
                }
            }
        }# end if ($null -ne $item.natgw_name){
    }# end foreach ($item in $myChecks.networks){
    # Create the Nagios report and configuration files
    if ($ERROR_STATE){
        Write-Output "WARNING" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    Write-Output "NAT GATEWAY REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Nat Gateway Name____Status" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "===============================" | Out-File -FilePath $TEMP_PATH -Append
    $count = 0
    while ($count -le $natGwCount){
        $output = $natGwObjects.$count.'display-name' + '                ' + $natGwObjects.$count.'lifecycle-state'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count +1
    }
    Copy-Item $TEMP_PATH -Destination $NGW_FILE_PATH
    Remove-Item -Path $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociNatGw_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_natgw_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 NGW"
    $NagiosConfigurationFile.service_file           = "ociNatGw_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI NATGW Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_natgw_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
} # end function CheckNatGw
function CheckNfsService(){
    # this function prepares Nagios plugin report and configuration files as follows:
    # 1) Get the compartment
    # 2) Get the availability domains for the compartment in the specified region
    # 3) Parse through the availability domain list and search file storage and mount
    #    points within each domain
    # 4) Only add to the dictionary if the specified file service and mount point are
    #    found in the availability domain
    # 5) report on file services health
    # 6) report on mount point healt
    # 7) prepare the Nagios configuration files
    $ERROR_STATE = $false
    $TEMP_PATH          = $Path + '/logs/nagios_plugin_nfs_temp.txt'
    $FILE_SERVICE_PATH  = $Path + '/logs/fileservice_statuses.txt'
    $nfsObjects  = @{}
    $mtObjects   = @{}
    $nfsCount    = 0
    $mtCount     = 0
    foreach ($item in $myChecks.fileStorage){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        $myAvailabilityDomains = GetAvailabilityDomains $item.region
        foreach ($AD in $myAvailabilityDomains.data){
            $myFileSystems = GetFileSystems $myCompartment $AD.name $item.region
            $myFileSystem = GetFileSystem $myFileSystems $item.file_service_name
            if ($null -ne $myFileSystem){
                $nfsObjects.Add($nfsCount, $myFileSystem)
                $nfsCount = $nfsCount + 1
                if ($myFileSystem.'lifecycle-state' -ne 'active'){$ERROR_STATE = $true}
            }
            $myMountTargets = GetMountTargets $myCompartment $AD.name $item.region
            $myMountTarget = GetMountTarget $myMountTargets $item.mount_target
            if ($null -ne $myMountTarget){
                $mtObjects.Add($mtCount, $myMountTarget)
                $mtCount = $mtCount + 1
                if ($myMountTarget.'lifecycle-state' -ne 'ACTIVE'){$ERROR_STATE = $true}
            }
        }# end foreach ($AD in $myAvailabilityDomains.data){
    }# end foreach ($item in $myChecks.fileStorage){
    
    # create the Nagios report and config files
    if ($ERROR_STATE){
        Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    Write-Output "FILE SYSTEM SERVICE REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "File Systems" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Filesystem Name____Availability Domain_____Status" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "====================================================" | Out-File -FilePath $TEMP_PATH -Append
    $count = 0
    while ($count -le $nfsCount){
        $output = $nfsObjects.$count.'display-name' + '         ' + `
            $nfsObjects.$count.'availability-domain' + '    ' + `
            $nfsObjects.$count.'lifecycle-state'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count + 1
    }

    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "MOUNT TARGET SERVICE REPORT" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "Mount Target Name____Availability Domain_____Status" | Out-File -FilePath $TEMP_PATH -Append
    Write-Output "======================================================" | Out-File -FilePath $TEMP_PATH -Append
    $count = 0
    while ($count -le $mtCount){
        $output = $mtObjects.$count.'display-name' + '        ' + `
            $mtObjects.$count.'availability-domain' + '    ' + `
            $mtObjects.$count.'lifecycle-state'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count + 1
    }

    Copy-Item $TEMP_PATH -Destination $FILE_SERVICE_PATH
    Remove-Item -Path $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociFileService_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_fserv_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 FSERVICE"
    $NagiosConfigurationFile.service_file           = "ociFileService_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI FILE SERVICE Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_fserv_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}
function CheckSubnets(
    [parameter(Mandatory=$true)]
        [string]$myPath
){
    $ERROR_STATE   = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin_subnet_temp.txt'
    $SUBNET_FILE_PATH   = $myPath + '/logs/subnet_statuses.txt'
    $subnetObjects = @{}
    $subnetCount   = 0
    foreach ($item in $myChecks.networks){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }
        $compartment_name = $item.compartment_name
        if ($networkObjects.$compartment_name.'display-name' -eq $item.vcn_name){
            $myVcn = $networkObjects.$compartment_name
            $myPrimaryRegionSubnets = oci network subnet list `
                --compartment-id $myCompartment.id `
                --vcn-id $myVcn.id `
                --all `
                | ConvertFrom-Json -AsHashtable
            foreach ($mySubnet in $myPrimaryRegionSubnets.data){
                if ($mySubnet.'lifecycle-state' -ne 'TERMINATED'){
                    if ($mySubnet.'lifecycle-state' -ne 'AVAILABLE'){
                        $ERROR_STATE = $true
                    }
                    $subnetObjects.add($subnetCount, $mySubnet)
                    # $subnetObjects.$subnetCount.'display-name'
                    $subnetCount = $subnetCount + 1
                }
            }
        }# end if ($networkObjects.$compartment_name.'display-name'.Contains($item.vcn_name)){

        # we have to check the DR region as well
        $myVcns = GetVcn $myCompartment $item.dr_region
        $myVcn  = SelectVcn $item.vcn_name $myVcns
        $mySecondarySubnets = GetSubnet $myCompartment $myVcn $item.dr_region
        if ($mySecondarySubnets){
            foreach ($mySubnet in $mySecondarySubnets.data){
                if ($mySubnet.'lifecycle-state' -ne 'TERMINATED'){
                    if ($mySubnet.'lifecycle-state' -ne 'AVAILABLE'){
                        $ERROR_STATE = $true
                    }
                    $subnetObjects.Add($subnetCount, $mySubnet)
                    # $subnetObjects.$subnetCount.'display-name'
                    $subnetCount = $subnetCount + 1
                }
            }
        }
        Remove-Variable myVcn 2> $null
    }# end foreach ($item in $myChecks.networks){

    if ($ERROR_STATE){
        Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH
    } else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }
    $count = 0
    while ($count -le $subnetCount){
        $output = $subnetObjects.$count.'display-name' + '        ' + $subnetObjects.$count.'lifecycle-state'
        Write-Output $output | Out-File -FilePath $TEMP_PATH -Append
        $count = $count + 1
    }
    Copy-Item $TEMP_PATH -Destination $SUBNET_FILE_PATH
    Remove-Item -Path $TEMP_PATH
    $NagiosConfigurationFile.command_file           = "ociSubnet_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_subnet_oci"
    $NagiosConfigurationFile.command_line           = "command_line" + " " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 SUBNET"
    $NagiosConfigurationFile.service_file           = "ociSubnet_services.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI SUBNET Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_subnet_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
}# end function CheckSubnets

function GetVCNObjects(){
    foreach ($item in $myChecks.networks){
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
                $vcns = GetVcn $myCompartment $item.region
                foreach ($vcn in $vcns.data){
                    if ($vcn.'display-name' -eq $item.vcn_name -and $vcn.'lifecycle-state' -ne 'TERMINATED'){
                        $compartment_name = $item.compartment_name
                        $networkObjects.add($compartment_name, $vcn)
                    }
                }
            }
        }
    }
}# end function GetVCNs


function GetVmObjects()
{
    foreach ($item in $myChecks.backups){
        # $item
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name -eq $item.compartment_name){
                $myCompartment = $compartment
            }
        }
        # we need the VMs within the compartment
        $VMs = oci compute instance list `
            --compartment-id $myCompartment.id `
            --region $item.region `
            --all `
            | ConvertFrom-Json -AsHashtable
        
        $vmsInCompartment = @{}
        foreach ($VM in $VMs.data){
            if ($VM.'lifecycle-state' -ne 'TERMINATED'){
                # Add the VM, the boot & block vol attachments to separate dicts. Then
                # add to the dict object $vmObjects. This will later be used for
                # the Nagios backup report within the function CheckBackups.
                $vmName = $VM.'display-name'
                $vmObj = @{}
                $vmObj.Add("instanceProperties", $VM)
                # $vmObj.Add("blockvolAttachment", $vmBlockVolAttachment)
                $vmsInCompartment.Add($vmName.ToUpper(), $vmObj)
                $bootVols = GetBootVolumes $VM $item.region
                $vmBootVolAttachment = SelectBootVolume $VM $bootVols
                $vmObj.Add("bootvolAttachment", $vmBootVolAttachment)
                $myBlockVolumes = GetBlockVolumes $VM $item.region
                # $myBlockVolumes.data
                $myBlockVolAttachment = SelectBlockVolume $VM $myBlockVolumes
                $vmObj.Add("blockvolAttachment", $myBlockVolAttachment)
            }
        }
        $compartment_name = $item.compartment_name
        $vmObjects.Add($compartment_name.ToUpper(),$vmsInCompartment)
    }
}# end function GetVmObjects
function checkVcns(
    [parameter(Mandatory=$true)]
        [string]$myPath
)
{
    # each object shall be checked. We start with the VCNs and all children of the VCNs
    # We set $ERROR_STATE=$False, and only set it to $true if an object is not reported
    # in a correct status. We may reset $ERROR_STATE again to false if multiple errors 
    # are detected. This is OK to do recursively. Once set to $False, always $False for
    # each class of objects checked. We will reset to $True on exit of the class check
    # prior to checking the next class of objects.
    $ERROR_STATE = $false
    $TEMP_PATH          = $myPath + '/logs/nagios_plugin__vcn_temp.txt'
    $VCN_FILE_PATH      = $myPath + '/logs/vcn_statuses.txt'
    # $TenantObjects.ChildCompartments
    $vcnObjects = @{}   # our dict object
    $vcnCounter = 0     # will be the unique key identifier for each hash key
    foreach ($item in $myChecks.networks){
        $compartment_name = $item.compartment_name
        # $networkObjects.$compartment_name
        if ($networkObjects.$compartment_name.'display-name' -eq $item.vcn_name){
            $vcn =  oci network vcn get `
                --vcn-id $networkObjects.$compartment_name.id `
                --region $item.region `
                | ConvertFrom-Json -AsHashtable
        }
        # we do this stupid stuff here because of the stupid way the OCI APIs return things
        $myVcn = $vcn.data
        foreach ($compartment in $TenantObjects.ChildCompartments.data){
            if ($compartment.name.Contains($item.compartment_name)){
                $myCompartment = $compartment
            }
        }

        if ($null -ne $myVcn){
            # Write-Output "got this far"
            # add to the hash key, then keep count of the number of VCNs found
            $vcnObjects.Add($vcnCounter, $myVcn)
            # $vcnObjects.$vcnCounter.'display-name'
            $vcnCounter = $vcnCounter +1
            # $vcnCounter
            if ($myVcn.'lifecycle-state' -ne 'AVAILABLE'){
                # only change $ERROR_STATE to $true if the VCN is not AVAILABLE
                $ERROR_STATE = $false
            }
        } else {
            # Only run this code if the other region needs to be checked for a VCN
            # do everything else the same way
            $myVcns = GetVcn $myCompartment $item.dr_region
            $myVcn  = SelectVcn $item.vcn_name $myVcns
            if ($myVcn.'lifecycle-state' -ne 'TERMINATED'){
                $vcnObjects.Add($vcnCounter, $myVcn)
                # $vcnObjects.$vcnCounter.'display-name'
                $vcnCounter = $vcnCounter +1
                # $vcnCounter
                if ($myVcn.'lifecycle-state' -ne 'AVAILABLE'){
                    $ERROR_STATE = $false
                }
            }
        }
        # We found it is necessary to clear this var after each iteration in order for the logic to work as expected
        Remove-Variable vcn 2> $null
        Remove-Variable myVcn 2> $null
    }# end foreach ($item in $myChecks.networks){
    # If any resource is not in an AVAILABLE state as determined above, write "Critical"
    # to the text file, otherwise, write "OK". This will be checked by the Nagios
    # plugin.
    if ($ERROR_STATE){Write-Output "CRITICAL" | Out-File -FilePath $TEMP_PATH}else {
        Write-Output "OK" | Out-File -FilePath $TEMP_PATH
    }

    $count = 0
    while ($count -le $vcnCounter){
        $output = $vcnObjects.$count.'display-name' + "         " + $vcnObjects.$count.'lifecycle-state'
        $count = $count + 1
        Write-Output $output | Out-File $TEMP_PATH -Append
    }
    Copy-Item $TEMP_PATH -Destination $VCN_FILE_PATH 
    Remove-Item -Path $TEMP_PATH
    # Create the Nagios configuration files
    $NagiosConfigurationFile.command_file           = "ociVcn_commands.cfg"
    $NagiosConfigurationFile.command_name           = "command_name check_vcn_oci"
    $NagiosConfigurationFile.command_line           = "command_line " + "$" + "USER1" + "$" + "/nagios_plugin.ps1 VCN"
    $NagiosConfigurationFile.service_file           = "ociVcn_service.cfg"
    $NagiosConfigurationFile.use                    = "use                 local-service"
    $NagiosConfigurationFile.host_name              = "host_name           localhost"
    $NagiosConfigurationFile.service_description    = "service_description OCI VCN Status"
    $NagiosConfigurationFile.check_command          = "check_command       check_vcn_oci"
    CreateNagiosConfigurationFiles $NagiosConfigurationFile
} # end function checkVcns

function CreateNagiosConfigurationFiles(
    [parameter(Mandatory=$true)]
        [array]$myNagiosConfigurationFile
){
    $outFile = $Path + "/logs/" + $NagiosConfigurationFile.command_file
    $output = "# Nagios configuration file " + $NagiosConfigurationFile.command_file
    Write-Output $output | Out-File -FilePath $outFile
    Write-Output "# Created by DKC Nagios Plugin nagios_swake.ps1" | Out-File -FilePath $outFile -Append
    Write-Output "" | Out-File -FilePath $outFile -Append
    Write-Output "# Copy to /usr/local/nagios/import and then import into Nagios to add service monitor" | Out-File -FilePath $outFile -Append
    Write-Output "" | Out-File -FilePath $outFile -Append
    Write-Output "define command{" | Out-File -FilePath $outFile -Append
    $output = "    " + $NagiosConfigurationFile.command_name
    Write-Output $output | Out-File -FilePath $outFile -Append
    $output = "    " + $NagiosConfigurationFile.command_line
    Write-Output $output | Out-File -FilePath $outFile -Append
    Write-Output "}" | Out-File -FilePath $outFile -Append
    Write-Output "" | Out-File -FilePath $outFile -Append
    Write-Output "# end of file" | Out-File -FilePath $outFile -Append
    
    $outFile = $Path + "/logs/" + $NagiosConfigurationFile.service_file
    $output = "# Nagios configuration file " + $NagiosConfigurationFile.service_file
    Write-Output $output | Out-File -FilePath $outFile
    Write-Output "# Created by DKC Nagios Plugin nagios_swake.ps1" | Out-File -FilePath $outFile -Append
    Write-Output "" | Out-File -FilePath $outFile -Append
    Write-Output "# Copy to /usr/local/nagios/import and then import into Nagios to add service monitor" | Out-File -FilePath $outFile -Append
    Write-Output "" | Out-File -FilePath $outFile -Append
    Write-Output "define service{" | Out-File -FilePath $outFile -Append
    $output = "    " + $NagiosConfigurationFile.use
    Write-Output $output | Out-File -FilePath $outFile -Append
    $output = "    " + $NagiosConfigurationFile.host_name
    Write-Output $output | Out-File -FilePath $outFile -Append
    $output = "    " + $NagiosConfigurationFile.service_description
    Write-Output $output | Out-File -FilePath $outFile -Append
    $output = "    " + $NagiosConfigurationFile.check_command
    Write-Output $output | Out-File -FilePath $outFile -Append
    Write-Output "}" | Out-File -FilePath $outFile -Append
    Write-Output "" | Out-File -FilePath $outFile -Append
    Write-Output "# end of file" | Out-File -FilePath $outFile -Append
}# end function CreateNagiosConfigurationFiles