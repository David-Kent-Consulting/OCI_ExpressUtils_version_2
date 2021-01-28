import os
import os.path

class GetVolumes:
    
    def __init__(
        self,
        block_storage_client,
        availability_domains,
        compartment_id):
        
        self.block_storage_client = block_storage_client
        self.availability_domains = availability_domains
        self.compartment_id = compartment_id
        self.block_volumes = []
        self.boot_volumes = []

        
    def populate_boot_volumes(self):
        
        if len(self.boot_volumes) != 0:
            return None
        else:
            # We have to walk down each availability domain to check for boot volumes
            for availability_domain in self.availability_domains:
                results = self.block_storage_client.list_boot_volumes(
                    availability_domain = availability_domain.name,
                    compartment_id = self.compartment_id).data
                for boot_volume in results:
                    if boot_volume.lifecycle_state == "AVAILABLE":
                        self.boot_volumes.append(boot_volume)

    def populate_block_volumes(self):
        
        if len(self.block_volumes) != 0:
            return None
        else:
            # We have to walk down each availability domain to check for boot volumes
            for availability_domain in self.availability_domains:
                results = self.block_storage_client.list_volumes(
                    availability_domain = availability_domain.name,
                    compartment_id = self.compartment_id).data
                for block_volume in results:
                    if block_volume.lifecycle_state != "TERMINATED":
                        self.block_volumes.append(block_volume)
    
    def return_boot_volume(self, boot_volume_id):
        
        for boot_volume in self.boot_volumes:
            if boot_volume.id == boot_volume_id:
                return boot_volume
    
    def return_block_volume(self, block_volume_id):
        
        for block_volume in self.block_volumes:
            if block_volume.id == block_volume_id:
                return block_volume
    
    def __str__(self):
        return "Class setup to perform tasks for block and boot volume tasks within compartment ID " + self.compartment_id

# end class GetVolumes

class GetVolumeBackups:
    
    def __init__(
        self,
        block_volume_client,
        compartment_id):
        
        self.block_volume_client = block_volume_client
        self.compartment_id = compartment_id
        self.block_volume_backups = []
        self.boot_volume_backups = []
        
    def populate_boot_volume_backups(self):
        
        if len(self.boot_volume_backups) != 0:
            return None
        else:
            self.boot_volume_backups = self.block_volume_client.list_boot_volume_backups(
                compartment_id = self.compartment_id,
                sort_by = "TIMECREATED").data

    def populate_block_volume_backups(self):
        
        if len(self.block_volume_backups) != 0:
            return None
        else:
            self.block_volume_backups = self.block_volume_client.list_volume_backups(
                compartment_id = self.compartment_id,
                sort_by = "TIMECREATED").data
            
    def return_block_volume_backups(self, volume_id):

        results = []
        for block_volume_backup in self.block_volume_backups:
            if block_volume_backup.volume_id == volume_id:
                results.append(block_volume_backup)
        
        return results
    
    def return_most_recent_active_block_volume_backup(self, volume_id):
        
        for block_volume_backup in self.block_volume_backups:
            if block_volume_backup.volume_id == volume_id and block_volume_backup.lifecycle_state == "AVAILABLE":
                
                return(block_volume_backup)
        
    
    def return_boot_volume_backups(self, boot_volume_id):
        
        results = []
        for boot_volume in self.boot_volume_backups:
            #print(boot_volume.boot_volume_id)
            if boot_volume.boot_volume_id == boot_volume_id:
                results.append(boot_volume)
                
        return results
    
    def return_most_recent_active_boot_volume_backup(self, boot_volume_id):
        
        results = []
        for boot_volume_backup in self.boot_volume_backups:
            if boot_volume_backup.boot_volume_id == boot_volume_id and boot_volume_backup.lifecycle_state == "AVAILABLE":
                
                return boot_volume_backup

# end class GetVolumeBackups

def attach_paravirtualized_volume(
    compute_composite_client,
    AttachParavirtualizedVolumeDetails,
    instance_id,
    volume_id,
    display_name,
    ):
    '''
    The purpose of this function is to attach a block volume to a
    VM instance in paravirtualized mode. Your code must check the status of
    the volume prior to calling this function. You must supply the
    instance_id and volume_id. The function returns the RESTFUL state
    of the object upon completion. The VM instance must be in a RUNNING state
    prior to calling this function.
    '''
    attach_volume_details = AttachParavirtualizedVolumeDetails(
        type = "paravirtualized",
        instance_id = instance_id,
        volume_id = volume_id,
        is_read_only = False,
        is_shareable = False
    )
    
    attach_volume_response = compute_composite_client.attach_volume_and_wait_for_state(
        attach_volume_details = attach_volume_details,
        wait_for_states = ["ATTACHED", "DETACHED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    return attach_volume_details

# end function def attach_paravirtualized_volume

def create_block_volume(
    storage_composite_client,
    CreateVolumeDetails,
    volume_name,
    availability_domain,
    compartment_id,
    volume_performance,
    size_in_gbs):
    '''
    This function will create a new volume that can be attached to a VM instance.
    It returns the resource creation response on success or None if the REST API
    call fails. Your code must handle duplicate avoidance, error handling, etc.
    '''
    
    if volume_performance == "LOW":
        vpus_per_gb = 0
    elif volume_performance == "BALANCED":
        vpus_per_gb = 10
    elif volume_performance == "HIGH":
        vpus_per_gb = 20

    create_volume_response = storage_composite_client.create_volume_and_wait_for_state(
        create_volume_details = CreateVolumeDetails(
            availability_domain = availability_domain,
            compartment_id = compartment_id,
            display_name = volume_name,
            vpus_per_gb = vpus_per_gb,
            size_in_gbs = size_in_gbs
        ),
        wait_for_states = ["AVAILABLE", "TERMINATED", "TERMINATING", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    if create_volume_response is not None:
        return create_volume_response
    else:
        return None

#end function create_block_volume()

def restore_block_volume(
    block_storage_composite_client,
    VolumeSourceFromVolumeBackupDetails,
    VolumeSourceDetails,
    CreateVolumeDetails,
    new_volume_name,
    availability_domain,
    compartment_id,
    size_in_gbs,
    backup_source_id):
    '''
    This function restores a block volume using the specified backup_source_id
    within the specified compartment. It waits for a state of AVAILABLE
    or an erroneous state of TERMINATED or UNKNOWN_ENUM_VALUE, and then
    returns the result to the calling code. Your code must handle avoiding
    creating boot volumes with duplicate display names. OCI does not
    enforce this.
    '''
    
    create_volume_details = CreateVolumeDetails(
        availability_domain = availability_domain,
        compartment_id = compartment_id,
        display_name = new_volume_name,
        size_in_gbs = size_in_gbs,
        source_details = VolumeSourceFromVolumeBackupDetails(
            type = "volumeBackup",
            id = backup_source_id
        )
    )
    results = block_storage_composite_client.create_volume_and_wait_for_state(
        create_volume_details = create_volume_details,
        wait_for_states = ["AVAILABLE", "TERMINATED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    return results

# end of function restore_block_volume()

def restore_boot_volume(
    block_storage_composite_client,
    BootVolumeSourceFromBootVolumeBackupDetails,
    BootVolumeSourceDetails,
    CreateBootVolumeDetails,
    new_boot_volume_name,
    availability_domain,
    compartment_id,
    size_in_gbs,
    backup_source_id
    ):
    '''
    This function restores a boot volume using the specified backup_source_id
    within the specified compartment. It waits for a state of AVAILABLE
    or an erroneous state of TERMINATED or UNKNOWN_ENUM_VALUE, and then
    returns the result to the calling code. Your code must handle avoiding
    creating boot volumes with duplicate display names. OCI does not
    enforce this.
    '''
    create_boot_volume_response = block_storage_composite_client.create_boot_volume_and_wait_for_state(
        create_boot_volume_details = CreateBootVolumeDetails(
            availability_domain = availability_domain,
            compartment_id = compartment_id,
            source_details = BootVolumeSourceFromBootVolumeBackupDetails(
                type="bootVolumeBackup",
                id = backup_source_id
            ),
            display_name = new_boot_volume_name,
            size_in_gbs = size_in_gbs
        ),
        wait_for_states = ["AVAILABLE", "TERMINATED", "UNKNOWN_ENUM_VALUE"]
    )
    
    return create_boot_volume_response.data

# end of function restore_boot_volume()