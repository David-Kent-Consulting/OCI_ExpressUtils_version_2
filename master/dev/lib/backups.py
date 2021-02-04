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

def create_volume_backup_policy(
    storage_client,
    CreateVolumeBackupPolicyDetails,
    UpdateVolumeBackupPolicyDetails,
    compartment_id,
    display_name,):
    '''
    This function creates a backup policy within the specified compartment. Unlike other
    OCI APIs, compartment_id is added to the class CreateVolumeBackupPolicyDetails, and then
    the storage client is called to create the policy. We choose to manage schedule MACDs
    in a separate function. As with all things OCI, your code must manage and avoid duplicates
    as well as exceptions.
    '''
    
    create_volume_backup_policy_details = CreateVolumeBackupPolicyDetails(
        compartment_id = compartment_id,
        display_name = display_name
    )
    
    create_backup_policy_request_results = storage_client.create_volume_backup_policy(
        create_volume_backup_policy_details = create_volume_backup_policy_details
    ).data
    
    return create_backup_policy_request_results

# end function create_volume_backup_policy()

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
    backup_job_frequency as either "ONE_HOUR", "ONE_DAY", "one_week", ONE_MONTH", "ONE_YEAR",
    and retention_in_days with a value between 1 and 2549. The function handles all
    of the othger calculations that the API is expecting.
    '''
    
    # Prefill values based on input and test input
    if backup_type not in ["FULL", "INCREMENTAL"]:
        raise RuntimeWarning("INVALID value for backup_type, Valid values are 'FULL' or 'INCREMENTAL'")
    
    if backup_job_frequency not in ["ONE_HOUR", "ONE_DAY", "ONE_WEEK", "ONE_MONTH", "ONE_YEAR"]:
        raise RuntimeWarning("INVALID value for backup_job_frequency, Valid valies are 'ONE_DAY', 'ONE_WEEK', 'ONE_MONTH', 'ONE_YEAR'")
        
    if retention_in_days < 1 and retention_in_days > 2549:
        raise RuntimeWarning("INVALID value for retention_in_days, must be an int between 1 and 2549")
    else:
        retention_seconds = retention_in_days * 86400
    
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
    
    schedule = VolumeBackupSchedule(
            backup_type = backup_type,
            period = backup_job_frequency,
            retention_seconds = retention_seconds,
            offset_seconds = 60 * 60, # we want to randomize the start time within a 60 minute window
            hour_of_day = start_time,
            day_of_week = day_of_week,
            month = month,
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