import os
import os.path

class GetVolumeAttachment:
    
    '''
    The purpose of this class is to get volume attachments for a compartment
    within a specified region. The methods in the class also return either all
    volume attachments or a specific volume when passed the volume OCID.
    '''
    
    def __init__(
        self,
        compute_client,
        compartment_id
    ):
        
        self.compute_client     = compute_client
        self.compartment_id     = compartment_id
        self.volume_attachments = []
        
    def populate_volume_attachments(self):
        if len(self.volume_attachments) != 0:
            return None
        
        results = self.compute_client.list_volume_attachments(
            compartment_id = self.compartment_id
        ).data

        for va in results:
            if va.lifecycle_state == "ATTACHED":
                self.volume_attachments.append(va)
    
    
    def return_all_vol_attachments(self):
        if len(self.volume_attachments) == 0:
            return None
        else:
            return self.volume_attachments
    
    def return_vol_attachment(self, volume_id):
        if len(self.volume_attachments) == 0:
            return None
        else:
            for va in self.volume_attachments:
                if va.volume_id == volume_id:
                    return va

                
    def __str__(self):
        
        return "class setup to return volume attachments from " + self.compartment_id

# end class GetVolumeAttachment

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
                    if boot_volume.lifecycle_state != "TERMINATED":
                        if boot_volume.lifecycle_state != "TERMINATING":
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
                        if block_volume.lifecycle_state != "TERMINATING":
                            self.block_volumes.append(block_volume)
    
    def return_boot_volume(self, boot_volume_id):
        
        for boot_volume in self.boot_volumes:
            if boot_volume.id == boot_volume_id:
                return boot_volume
    
    def return_boot_volume_by_name(self, volume_name):

        for boot_volume in self.boot_volumes:
            if boot_volume.display_name == volume_name:
                return boot_volume
    
    def return_block_volume(self, block_volume_id):
        
        for block_volume in self.block_volumes:
            if block_volume.id == block_volume_id:
                return block_volume

    def return_block_volume_by_name(self, volume_name):

        for block_volume in self.block_volumes:
            if block_volume.display_name == volume_name:
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

def attach_iscsi_volume(
    compute_composite_client,
    AttachIScsiVolumeDetails,
    instance_id,
    volume_id,
    display_name
    ):
    '''
    This function attaches a volume to a VM instance using the iSCSI protocol.
    This is faster versus the typical paravirtualized attachment but requires
    additional sysadmin overhead on the OS to make the kernel aware of the
    attachment.

    We have found iSCSI attaching can sometimes fail due to OCI issues. Your
    code must check the response to ensure the attachment is successful.
    '''
    
    attach_volume_details = AttachIScsiVolumeDetails(
        type = "iscsi",
        instance_id = instance_id,
        volume_id = volume_id,
        display_name = display_name,
        is_read_only = False,
        is_shareable = False
    )
    
    attach_volume_response = compute_composite_client.attach_volume_and_wait_for_state(
        attach_volume_details = attach_volume_details,
        wait_for_states = ["ATTACHED", "DETACHED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    return attach_volume_response

# end function attach_iscsi_volume()

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

    Generally speaking, paravirtualized attaching is more reliable than iSCSI
    attachments, and has lower admin work on the host. The performance is lower.
    iSCSI attachments should be used when high performance is needed.

    Your code should check the response to ensure the attachment was successful.
    '''
    attach_volume_details = AttachParavirtualizedVolumeDetails(
        type = "paravirtualized",
        instance_id = instance_id,
        volume_id = volume_id,
        display_name = display_name,
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

def delete_volume(
    storage_composite_client,
    volume_id
    ):
    '''
    This function will delete a volume. The volume should not be attached to a
    VM instance prior to calling. It returns a response on success, or
    None on failure
    '''
    
    results = storage_composite_client.delete_volume_and_wait_for_state(
        volume_id = volume_id,
        wait_for_states = ["TERMINATED", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    )
    
    if results is not None:
        return results
    else:
        return None
    
# end function delete_volume()

def delete_volume_attachment(
    compute_composite_client,
    volume_attachment_id):
    '''
    This function detaches a volume from a VM instance. We recommend that your code
    ensures the VM instance is gracefully shutdown prior to calling this function.
    OCI will not prevent detachment of a volume when a VM instance is running.
    Detaching a volume from a running VM instance with a running kernel can be
    risky. Your code must handle the conditions you intend in a safe and proper
    manner.
    
    The function returns the results of the detachment request, or None if
    no response is received. 
    '''
    
    results = compute_composite_client.detach_volume_and_wait_for_state(
        volume_attachment_id = volume_attachment_id,
        wait_for_states = ["DETACHED", "UNKNOWN_ENUM_VALUE"]
    )
    
    if results is None:
        return None
    else:
        return results
    
# end function delete_volume_attachement()


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

def increase_volume_size(
    storage_composite_client,
    UpdateVolumeDetails,
    volume_id,
    size_in_gbs):
    '''
    This function increases a volume's size. This is safe to run when the VM is
    in a running state. Note however that the sysadmin will have to re-poll
    the OS disk devices to detect the change. OCI will not allow decreasing the
    volume size. Your code must check for illegal conditions prior to calling
    this function.
    
    Your code must check the response for expected results.
    '''
    
    update_volume_details = UpdateVolumeDetails(
        size_in_gbs = size_in_gbs
    )
    
    results = storage_composite_client.update_volume_and_wait_for_state(
        volume_id = volume_id,
        update_volume_details = update_volume_details,
        wait_for_states = ["AVAILABLE", "TERMINATED", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    )
    
    if results is not None:
        return results
    else:
        return None

# end function increase_volume_size()

def update_volume_performance(
    storage_composite_client,
    UpdateVolumeDetails,
    volume_id,
    volume_performance):
    '''
    This function will modify a volume's performance by increasing or decreasing
    the number of CPUs per GB to the volume. Although not required by OCI,
    we recommend that the VM instance be shutdown when applying this change.
    
    The var volume_performance must be LOW, BALANCED, or HIGH. The function sets
    the number of assigned CPUs accordingly. It is notable that the OCI provided
    code example has a defect and should not be followed.
    '''
    
    if volume_performance == "LOW":
        vpus_per_gb = 0
    elif volume_performance == "BALANCED":
        vpus_per_gb = 10
    elif volume_performance == "HIGH":
        vpus_per_gb = 20
    update_volume_details = UpdateVolumeDetails(
        vpus_per_gb = vpus_per_gb
    )
    
    results = storage_composite_client.update_volume_and_wait_for_state(
        volume_id = volume_id,
        update_volume_details = update_volume_details,
        wait_for_states = ["AVAILABLE", "TERMINATED", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    )
    
    if results is not None:
        return results
    else:
        return None
    
# end function update_volume_performance()