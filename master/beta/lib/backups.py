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

import csv
import os
import os.path


class GetBackupPolicies:
    
    def __init__(
        self,
        storage_client,
        compartment_id):
        '''
        This class gets, stores, and retrieves volume backup policy data as determined
        by the class you call. Always instiate and then call populate_backup_policies()
        to get all backup policies within a compartment. Then call the other methods
        based on what you need to do. Note there is no value lifecycle_state with
        backup policies, so we do not check for that.
        '''
        
        self.storage_client = storage_client
        self.compartment_id = compartment_id
        self.volume_backup_policies = []
        
    def populate_backup_policies(self):
        
        if len(self.volume_backup_policies) != 0:
            return None
        else:
            results = self.storage_client.list_volume_backup_policies(
                compartment_id = self.compartment_id
            )
            for bp in results.data:
                self.volume_backup_policies.append(bp)
    
    def return_all_volume_backup_policies(self):
        
        if len(self.volume_backup_policies) == 0:
            return None
        else:
            return self.volume_backup_policies
        
    def return_volume_backup_policy(self, volume_backup_policy_name):
        
        if len(self.volume_backup_policies) == 0:
            return None
        else:
            for bp in self.volume_backup_policies:
                if bp.display_name == volume_backup_policy_name:
                    return bp

# end class GetBackupPolicies

class GetVolumeBackupItems:
    '''
    This class fetches and returns to the calling program data about boot and block volumes.
    It requires a storage client instance for both the primary and DR regions, as well as
    the volume type and volume ID. Your code must handle all pre-reqs and error conditions.

    OCI does not provide an efficient tool for a cloud user to get report information about
    volume backup snaps. This class, when used with other code, provides for a simplified
    means of identifying backups to a volume without depending on a policy name.

    Our does not presume that backups are replicated to a DR region, but we do require
    that a secondary region be provided since in most cases VM instance backup datta
    will be replicated between regions.

    CAUTION: This class may consume a significant amount of RAM off the heap. We recommend
    that your code take measures to ensure sufficient RAM prior to calling this code.

    Instiate the class, then call populate_backup_items() to get the backup data.

    return_all_backup_items() will return all backup resources that are found in the two
    regions provided when instiated. If no data is found, None is returned.
    return_all_dr_backup_items() works the same way.
    
    return_backup_item() and return_dr_backup_item() expect to receive a backup item name.
    If that item is found, it is returned, otherwise it returns None.

    return_backups_this_day() expects the date of the backup object to search for in the
    form of DD, MM, YYYY as three integer or string numeric values. It uses string
    concatenation and does a string compare to find the data in time_created in the
    REST backup object, which is instiated from datetime(). This provides for a straight
    forward means to search for that string in each object that we are keying on.
    Both regions are searched for and all backups found for that day are returned to
    your program.

    '''
    
    def __init__(
        self,
        storage_client,
        dr_storage_client,
        compartment_id,
        volume_type,
        volume_id):
        
        self.storage_client    = storage_client
        self.dr_storage_client = dr_storage_client
        self.compartment_id    = compartment_id
        
        if volume_type not in ["--BOOT-VOLUME", "--VOLUME"]:
            raise RuntimeWarning("INVALID VALUE! Value for volume_type must be --BOOT_VOLUME or --VOLUME")
        else:
            self.volume_type   = volume_type
        
        self.volume_id         = volume_id
        self.backup_items      = []
        self.dr_backup_items   = []
        
    def populate_backup_items(self):
        
        if len(self.backup_items) != 0:
            return None
        else:
            
            if self.volume_type == "--BOOT-VOLUME":
                list_volume_backups_response = self.storage_client.list_boot_volume_backups(
                    compartment_id = self.compartment_id,
                    boot_volume_id = self.volume_id
                ).data
                list_dr_volume_backup_response = self.dr_storage_client.list_boot_volume_backups(
                    compartment_id = self.compartment_id,
                    boot_volume_id = self.volume_id
                ).data
            elif self.volume_type == "--VOLUME":
                list_volume_backups_response = self.storage_client.list_volume_backups(
                    compartment_id = self.compartment_id,
                    volume_id = self.volume_id
                ).data
                list_dr_volume_backup_response = self.dr_storage_client.list_volume_backups(
                    compartment_id = self.compartment_id,
                    volume_id = self.volume_id
                ).data

                
            for backup_item in list_volume_backups_response:
                self.backup_items.append(backup_item)
            for backup_item in list_dr_volume_backup_response:
                self.dr_backup_items.append(backup_item)
                
    def return_all_backup_items(self):
        
        if len(self.backup_items) == 0:
            return None
        else:
            return self.backup_items
        
    def return_all_dr_backup_items(self):
        
        if len(self.dr_backup_items) == 0:
            return None
        else:
            return self.dr_backup_items
        
    def return_backup_item(self, backup_item_name):
        
        if len(self.backup_items) == 0:
            return None
        else:
            for backup_item in self.backup_items:
                if backup_item.display_name == backup_item_name:
                    return backup_item

    def return_dr_backup_item(self, backup_item_name):
        
        if len(self.dr_backup_items) == 0:
            return None
        else:
            for backup_item in self.dr_backup_items:
                if backup_item.display_name == backup_item_name:
                    return backup_item
                
    def return_backups_this_day(
        self,
        day_of_month,
        month_of_year,
        year):
        
        if len(self.backup_items) == 0:
            return None
        else:
            for backup_item in self.backup_items:
                if backup_item.time_created.strftime("%d%m%Y") == str(day_of_month) + str(month_of_year) + str(year):
                    return backup_item
                
    def return_dr_backups_this_day(
        self,
        day_of_month,
        month_of_year,
        year):
        
        if len(self.dr_backup_items) == 0:
            return None
        else:
            for backup_item in self.dr_backup_items:
                if backup_item.time_created.strftime("%d%m%Y") == str(day_of_month) + str(month_of_year) + str(year):
                    return backup_item
        
# end class GetVolumeBackupItems

def create_volume_backup_policy(
    storage_client,
    CreateVolumeBackupPolicyDetails,
    UpdateVolumeBackupPolicyDetails,
    compartment_id,
    destination_region,
    display_name):
    '''
    This function creates a backup policy within the specified compartment. Unlike other
    OCI APIs, compartment_id is added to the class CreateVolumeBackupPolicyDetails, and then
    the storage client is called to create the policy. We choose to manage schedule MACDs
    in a separate function. As with all things OCI, your code must manage and avoid duplicates
    as well as exceptions.
    '''
    
    create_volume_backup_policy_details = CreateVolumeBackupPolicyDetails(
        compartment_id = compartment_id,
        display_name = display_name,
        destination_region = destination_region
    )
    
    create_backup_policy_request_results = storage_client.create_volume_backup_policy(
        create_volume_backup_policy_details = create_volume_backup_policy_details
    ).data
    
    return create_backup_policy_request_results

# end function create_volume_backup_policy()

def add_volume_to_backup_policy(
    storage_client,
    CreateVolumeBackupPolicyAssignmentDetails,
    block_volume_id,
    policy_id):
    '''
    This function assigns a block volume to a volume backup policy. Previous
    policy assignments are superceded by this action. Function returns the
    assignment properties upon success. Your code must manage all pre-reqs
    and error handling.
    '''

    create_volume_backup_policy_assignment_details = CreateVolumeBackupPolicyAssignmentDetails(
        asset_id = block_volume_id,
        policy_id = policy_id
    )

    create_volume_backup_policy_assignment_response = storage_client.create_volume_backup_policy_assignment(
        create_volume_backup_policy_assignment_details = create_volume_backup_policy_assignment_details
    ).data

    return create_volume_backup_policy_assignment_response

# end function add_volume_to_backup_policy()

def delete_volume_backup_policy(
    storage_client,
    policy_id):
    '''
    This function deletes a backup policy from the specified compartment. Just
    pass to it the storage client and policy_id, and poof, its gone. The API
    does not return any data on completion regardless as to success or failure,
    so the best thing to do is either to fail out or to check for the policy's
    removal on exit.
    '''
    
    delete_backup_policy_results = storage_client.delete_volume_backup_policy(
        policy_id = policy_id
    )
    
    return delete_backup_policy_results

# end function delete_volume_backup_policy()

def add_backup_schedule(
    storage_client,
    UpdateVolumeBackupPolicyDetails,
    VolumeBackupSchedule,
    backup_policy,
    backup_type,
    day_of_week,
    month,
    start_time,
    backup_job_frequency,
    retention_in_days):
    '''
    This function adds a schedule to backup_policy. Existing schedules are retained
    if found. Your code provides backup_type as either "FULL" or "INCREMENTAL",
    backup_job_frequency as either "ONE_HOUR", "ONE_DAY", "ONE_WEEK", ONE_MONTH", "ONE_YEAR".
    day_of_week is the day of the week, in caps, that the schedule is to be run. day_of_week is
    ignored when backup_frequency is set to daily. Month is the calendar month to run a backup,
    start time is an int between 0 and 23 during which time the schedule is launched,
    backup_frequency is the API equivalent if "period" and accepts values as defined below,
    rentention in days is a value between 1 and 2549, for a maximum backup retention of 7 years.

    Your code must handle all pre-req conditions, such as restrictions on the type and schedule of
    backups. See the Oracle API doclink below:
    https://docs.oracle.com/en-us/iaas/tools/python/2.30.0/api/core/models/oci.core.models.VolumeBackupSchedule.html#oci.core.models.VolumeBackupSchedule 

    or see the Oracle doc link regarding OCI backup at:nn
    https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumebackups.htm 
    '''
    
    # Prefill values based on input and test input
    if backup_type not in ["FULL", "INCREMENTAL"]:
        raise RuntimeWarning("INVALID value for backup_type, Valid values are 'FULL' or 'INCREMENTAL'")
    
    if backup_job_frequency not in ["ONE_HOUR", "ONE_DAY", "ONE_WEEK", "ONE_MONTH", "ONE_YEAR"]:
        raise RuntimeWarning("INVALID value for backup_job_frequency, Valid valies are 'ONE_DAY', 'ONE_WEEK', 'ONE_MONTH', 'ONE_YEAR'")
    # The API is grossly weak in how it applies policies. offset_type must be set for monthly or annual backups to be enforced.
    # Otherwise, they are scheduled with the time offset, which will result in undefined program behavior.
    elif backup_job_frequency in ["ONE_MONTH", "ONE_YEAR"]:
        offset_type = "STRUCTURED"
    else:
        offset_type = None
        
    if retention_in_days < 1 and retention_in_days > 2549:
        raise RuntimeWarning("INVALID value for retention_in_days, must be an int between 1 and 2549")
    else:
        retention_seconds = retention_in_days * 24 * 60 * 60
    
    if start_time not in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]:
        raise RuntimeWarning("INVALID value for start_time, Valid value must be an int between 0 and 23")
    
    if day_of_week is not None:
        pass
        if day_of_week not in ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']:
            raise RuntimeWarning("INVALID value for day_of_week, Valid values are SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'")
    
    if month is not None:
        if month not in ['JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE','JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER']:
            raise RuntimeWarning("INVALID value for month, Valid values are 'JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE','JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER'")



    time_zone = "REGIONAL_DATA_CENTER_TIME"
    schedules = []
    if len(backup_policy.schedules) != 0:
        for sched in backup_policy.schedules:
            schedules.append(sched)
    '''
    The API is FUBAR with respect to offset_seconds and hour_of_day. hour_of_day is ignored. What
    matters is offset_seconds, which specifies the start time of the backup from either regional
    time or UTC time. So if your backups are in US-ASHBURN-1, and you have set start_time to
    23 for 23:00, the value of offset_seconds will calculate to 82800. We record hour_of_day
    because the API accepts it. By doing so, we'll have a sensible means of finding a schedule we
    may want to modify, delete, or omit from deletion.

    We have also found that the API will set day_of_week even when inapplicable. This and other weaknesses
    in this API probably stem back to the roots of Oracle having commercialized VirtualBox as the base
    of their hypervisor.
    '''
    schedule = VolumeBackupSchedule(
            backup_type = backup_type,
            period = backup_job_frequency,
            retention_seconds = retention_seconds,
            offset_type = offset_type,
            offset_seconds = start_time * 3600,
            hour_of_day = start_time,
            day_of_week = day_of_week,
            month = month,
            day_of_month = 1,
            time_zone = time_zone
        )
    schedules.append(schedule)
    update_volume_backup_policy_details = UpdateVolumeBackupPolicyDetails(
        schedules = schedules
    )
        
    update_volume_backup_policy_response = storage_client.update_volume_backup_policy(
        policy_id = backup_policy.id,
        update_volume_backup_policy_details = update_volume_backup_policy_details
    ).data
    
    return update_volume_backup_policy_response

# end function add_backup_schedule()

def check_schedule(
    backup_policy,
    backup_type,
    period,
    hour_of_day):
    '''
    This function checks for an existing backup policy and returns True if found, or False if not found
    '''

    for sched in backup_policy.schedules:
        # print(sched)
        if sched.backup_type == backup_type and sched.period == period \
            and sched.hour_of_day == hour_of_day:
            return True
        else:
            return False
# end function check_schedule()

def delete_backup_schedule(
    storage_client,
    UpdateVolumeBackupPolicyDetails,
    VolumeBackupSchedule,
    backup_policy,
    backup_type,
    period,
    hour_of_day):
    '''
    This function will remove a schedule from a backup policy. 4 objects are required to
    do this, 1) the complete backup_policy object, 2) the backup_type to search for,
    3) the backup_job_frequency of the object, and 4) start_time. Simple logic will step
    through the schedules and groom out the selected schedule. Then the reduced list
    of schedules are applied to the policy. We return a result from the REST API service
    if found, otherwise we make no changes and return None. Your code needs to handle any
    exceptions.
    '''
    
    schedules = []
    schedules_changed = False
    for sched in backup_policy.schedules:
        # print("Test     : " + backup_type + " " + period + " " + str(hour_of_day))
        if sched.backup_type == backup_type and sched.period == period \
          and sched.hour_of_day == hour_of_day:
            schedules_changed = True
            # print("delete schedule : " + sched.backup_type +" " + sched.period + " " + str(sched.hour_of_day))
        else:
            schedules.append(sched)



    
    if schedules_changed:
        
        update_volume_backup_policy_details = UpdateVolumeBackupPolicyDetails(
            schedules = schedules
        )
        update_volume_backup_policy_response = storage_client.update_volume_backup_policy(
            policy_id = backup_policy.id,
            update_volume_backup_policy_details = update_volume_backup_policy_details
        ).data
        return update_volume_backup_policy_response
    
    else:
        return None

# end function delete_backup_schedule()