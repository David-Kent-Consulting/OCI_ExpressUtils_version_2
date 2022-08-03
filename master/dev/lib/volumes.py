# Copyright 2019 – 2022 David Kent Consulting, Inc.
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

    def return_all_boot_volunes(self):

        if len(self.boot_volumes) == 0:
            return None
        else:
            return self.boot_volumes
    
    def return_boot_volume(self, boot_volume_id):
        
        for boot_volume in self.boot_volumes:
            if boot_volume.id == boot_volume_id:
                return boot_volume
    
    def return_boot_volume_by_name(self, volume_name):

        for boot_volume in self.boot_volumes:
            if boot_volume.display_name == volume_name:
                return boot_volume
    
    def return_all_block_volumes(self):

        if len(self.block_volumes) == 0:
            return None
        else:
            return self.block_volumes
    
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
        
        for boot_volume_backup in self.boot_volume_backups:
            if boot_volume_backup.boot_volume_id == boot_volume_id and boot_volume_backup.lifecycle_state == "AVAILABLE":
                return boot_volume_backup

    def return_backups_from_volume_id(self, volume_id, volume_type):

        if volume_type not in ["BOOT_VOLUME", "VOLUME"]:
            raise RuntimeError("EXCEPTION! volume_type must be BOOT_VOLUME or VOLUME")
        elif volume_type == "VOLUME":
            list_block_volume_backups_response = self.block_volume_client.list_volume_backups(
                compartment_id = self.compartment_id,
                volume_id = volume_id
            ).data
        elif volume_type == "BOOT_VOLUME":
            list_block_volume_backups_response = self.block_volume_client.list_boot_volume_backups(
                compartment_id = self.compartment_id,
                boot_volume_id = volume_id
            ).data

        return list_block_volume_backups_response


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
    
    return attach_volume_response

# end function def attach_paravirtualized_volume

def check_vm_replica_status(
    dr_storage_client,
    boot_volumes,
    block_volumes
    ):
    
    '''
    
    The purpose of this function is to test the status of volume replication for all
    volume types that are mapped to a VM. The function returns True if the test passes,
    or False if the test fails.
    
    We begin by walking down the boot volume list boot_volumes. The KENT code logic
    exists to gather this data using GetVolumeAttachment and GetVolumes.
    Your logic must distinguish between boot and block volumes accordingly so as to
    extract two lists. The list boot_volumes contains a simple list of object type
    BootVolume. The list block_volumes contains a simple list of object type Volumes.
    
    The logic in the function will start by checking each object in boot_volumes to
    ensure the list is not empty. Then we check each object in the list and make a
    call to get_boot_volume_replica and check lifecycle_state for a state of
    "AVAILABLE". We immediately return a state of False if any of the above
    conditions are not met.
    
    We test to see if the count of block_volumes is > 0, if not we exit the logic since
    a virtual machine may have no data disks. If the count is > 0, we repeat the same
    logic used for boot_volumes.
    
    If all goes well, the function ends by returning True.
    
    NOTE: dr_storage_client is a dict. object created by oci.config.fromfile(). You
    must make a copy of config to dr_config and modify the data vault for the key
    "region" to the correct string for the DR region. It is your responsibility to
    perform a pre-flight check on region and DR region exsitence prior to calling
    this function.
    
    WARNING! Our coding standards will not support concatenated volumes of any kind.
             Volume concatenation is not neceeeasry in OCI and will increase risk
             whilst decreasing performance. We do not consider volume concatination
             a best practice in OCI and will not support it under any conditions.
    
    '''
    
    for bv in boot_volumes:  # boot_volumes cannot be empty since a VM cannot exist without at
                             # least 1 boot boot volume. We are not concerned abpout the
                             # source volume's lifecycle state since this function is used to
                             # test a DR recovery scenario.
        
        if bv.boot_volume_replicas is None:
            return False     # failed condition
        else:
            # we always check position 0 of the list since we do not support volume
            # concatenation in OCI.
            get_boot_volume_replica_response = dr_storage_client.get_boot_volume_replica(
                boot_volume_replica_id = bv.boot_volume_replicas[0].boot_volume_replica_id
            )
            if get_boot_volume_replica_response.data.lifecycle_state != "AVAILABLE":
                return False # failed condition
    
    if block_volumes is not None: # block volumes can be empty, if so we fall through to
                                  # return True
        for v in block_volumes:
            if v.block_volume_replicas is None:
                return False      # failed condition
            else:
                # we always check position 0 of the list since we do not support volume
                # concatenation in OCI.
                get_block_volume_replica_response = dr_storage_client.get_block_volume_replica(
                    block_volume_replica_id = v.block_volume_replicas[0].block_volume_replica_id
                )
                if get_block_volume_replica_response.data.lifecycle_state != "AVAILABLE":
                    return False  # failed condition
    
    return True

# end function check_vm_replica_status

def create_boot_volume_from_replica(
    composite_storage_client,
    BootVolumeSourceFromBootVolumeReplicaDetails,
    CreateBootVolumeDetails,
    compartment_id,
    availability_domain,
    display_name,
    size_in_gbs,
    boot_volume_replica_id,
    vpus_per_gb
    ):
    
    '''
    
    This function creates a boot volume from a boot volume replica copy. Your logic
    must collect the applicable volume data and pass such to the function. The
    function immediately returns an object type BootVolume. The function returns
    an object type BootVolume on success or None on failure.
    
    WARNING! Your logic must test for duplicates prior to running this function.
    Use the KENT class GetVolumes or other tools to collect a list of volumes.
    Test to ensure the target name does not already exist prior to calling this
    function. A failure to do so will result in boot volumes with duplicate
    names.
   
    '''
    
    create_boot_volume_details = CreateBootVolumeDetails(
        compartment_id = compartment_id,
        availability_domain = availability_domain,
        display_name = display_name,
        size_in_gbs = size_in_gbs,
        source_details = BootVolumeSourceFromBootVolumeReplicaDetails(
            type="bootVolumeReplica",
            id = boot_volume_replica_id,
        ),
        vpus_per_gb = vpus_per_gb
    )
    
    create_boot_volume_response = composite_storage_client.create_boot_volume_and_wait_for_state(
        create_boot_volume_details = create_boot_volume_details,
        wait_for_states = ["AVAILABLE", "TERMINATING", "TERMINATED", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    )
    
    return create_boot_volume_response

# end function create_boot_volume_from_replica

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

def create_bootvol_replica(
    storage_client,
    UpdateBootVolumeDetails,
    BootVolumeReplicaDetails,
    boot_volume_id,
    availability_domain,
    boot_volume_display_name
    ):
    '''
    the API requires the availability domain identifier, not the name, as well as
    the display name for the replica. We choose to make the display name the
    same as the primary volume the replica spawns from. The volume AD is created
    from the primary volume AD name, the remote region key, the chars "-AD-",
    and the AD number that is derived from the primary volume AD number. This
    string is prepared by the logic that calls this function.
    '''
    update_boot_volume_details = UpdateBootVolumeDetails(
        display_name = boot_volume_display_name,
        boot_volume_replicas=[
            BootVolumeReplicaDetails(
                availability_domain = availability_domain,
                display_name = boot_volume_display_name
            )]
    )
    
    update_boot_volume_response = storage_client.update_boot_volume(
        boot_volume_id = boot_volume_id,
        update_boot_volume_details = update_boot_volume_details
    )
    
    return update_boot_volume_response
    
# end function create_bootvol_replica

def create_vol_replica(
    storage_client,
    UpdateVolumeDetails,
    BlockVolumeReplicaDetails,
    volume_id,
    availability_domain,
    volume_display_name
):
    '''
    the API requires the availability domain identifier, not the name, as well as
    the display name for the replica. We choose to make the display name the
    same as the primary volume the replica spawns from. The volume AD is created
    from the primary volume AD name, the remote region key, the chars "-AD-",
    and the AD number that is derived from the primary volume AD number. This
    string is prepared by the logic that calls this function.
    '''
    update_volume_details = UpdateVolumeDetails(
        display_name = volume_display_name,
        block_volume_replicas = [
            BlockVolumeReplicaDetails(
                availability_domain = availability_domain,
                display_name = volume_display_name)
        ]
    )
    
    
    update_volume_response = storage_client.update_volume(
        volume_id = volume_id,
        update_volume_details = update_volume_details
    )
    
    return update_volume_response

# def create_boot_volume_from_replica(
#     storage_client,
#     BootVolumeSourceFromBootVolumeReplicaDetails,
#     CreateBootVolumeDetails,
#     compartment_id,
#     availability_domain,
#     display_name,
#     size_in_gbs,
#     boot_volume_replica_id,
#     vpus_per_gb
#     ):
    
#     '''
    
#     This function creates a boot volume from a boot volume replica copy. Your logic
#     must collect the applicable volume data and pass such to the function. The
#     function immediately returns an object type BootVolume. The function returns
#     an object type BootVolume on success or None on failure.
    
#     WARNING! Your logic must test for duplicates prior to running this function.
#     Use the KENT class GetVolumes or other tools to collect a list of volumes.
#     Test to ensure the target name does not already exist prior to calling this
#     function. A failure to do so will result in boot volumes with duplicate
#     names.
    
#     '''
    
#     create_boot_volume_details = CreateBootVolumeDetails(
#         compartment_id = compartment_id,
#         availability_domain = availability_domain,
#         display_name = display_name,
#         size_in_gbs = size_in_gbs,
#         source_details = BootVolumeSourceFromBootVolumeReplicaDetails(
#             type="bootVolumeReplica",
#             id = boot_volume_replica_id,
#         ),
#         vpus_per_gb = vpus_per_gb
#     )
    
#     create_boot_volume_response = dr_storage_client.create_boot_volume(
#         create_boot_volume_details = create_boot_volume_details
#     )
    
#     if create_boot_volume_response.data.lifecycle_state not in ["CREATING", "AVAILABLE", "PROVISIONING"]:
#         return None  # failed operation
        
#     return create_boot_volume_response

# # end function create_boot_volume_from_replica


# end function create_vol_replica

def create_volume_from_volume_replica(
    storage_composite_client,
    CreateVolumeDetails,
    VolumeSourceFromBlockVolumeReplicaDetails,
    compartment_id,
    availability_domain,
    display_name,
    size_in_gbs,
    volume_replica_id,
    vpus_per_gb
    ):

    '''
    
    This function creates a volume from a boot volume replica copy. Your logic
    must collect the applicable volume data and pass such to the function. The
    function immediately returns an object type Volume. The function returns
    an object type Volume on success or None on failure.
    
    WARNING! Your logic must test for duplicates prior to running this function.
    Use the KENT class GetVolumes or other tools to collect a list of volumes.
    Test to ensure the target name does not already exist prior to calling this
    function. A failure to do so will result in volumes with duplicate
    names.
    
    '''

    create_volume_details = CreateVolumeDetails(
        compartment_id = compartment_id,
        availability_domain = availability_domain,
        display_name = display_name,
        size_in_gbs = size_in_gbs,
        source_details = VolumeSourceFromBlockVolumeReplicaDetails(
            type="blockVolumeReplica",
            id = volume_replica_id
            ),
        vpus_per_gb = vpus_per_gb
    )

    create_volume_response = storage_composite_client.create_volume_and_wait_for_state(
        create_volume_details = create_volume_details,
        wait_for_states = ["AVAILABLE", "TERMINATING", "TERMINATED", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    )
    
    return create_volume_response

# end function create_volume_from_volume_replica

def delete_bootvol_replica(
    storage_client,
    UpdateBootVolumeDetails,
    boot_volume_id,
    boot_volume_display_name
    ):
    '''
    This function deletes a volume replica by passing an empty list to
    the API. The net effect of this action will push a termination of the
    will be the REST service 1) dropping the linkage to the replica within
    the volume object, 2) terminating the replicated object in the replicated
    region/domain.
    '''
    
    
    update_boot_volume_details = UpdateBootVolumeDetails(
        display_name = boot_volume_display_name,
        boot_volume_replicas=[]
    )
    
    update_boot_volume_response = storage_client.update_boot_volume(
        boot_volume_id = boot_volume_id,
        update_boot_volume_details = update_boot_volume_details
    )
    
    return update_boot_volume_response

# end function def delete_bootvol_replica

def delete_vol_replica(
    storage_client,
    UpdateVolumeDetails,
    volume_id,
    volume_display_name
):
    '''
    This function deletes a volume replica by passing an empty list to
    the API. The net effect of this action will push a termination of the
    will be the REST service 1) dropping the linkage to the replica within
    the volume object, 2) terminating the replicated object in the replicated
    region/domain.
    '''
    
    update_volume_details = UpdateVolumeDetails(
        display_name = volume_display_name,
        block_volume_replicas = []
    )
    
    update_volume_response = storage_client.update_volume(
        volume_id = volume_id,
        update_volume_details = update_volume_details
    )
    
    return update_volume_details
    
# end function delete_vol_replica

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

def update_volume_name(
    storage_composite_client,
    UpdateVolumeDetails,
    volume_id,
    display_name
    ):
    '''
    This function modifies a volume name to a new name. Your code must check to avoid
    creating a duplicate name. The function returns the results. Your code must check
    the results and take action as approrpiate.
    '''

    results = storage_composite_client.update_volume_and_wait_for_state(
        volume_id = volume_id,
        update_volume_details = UpdateVolumeDetails(
            display_name = display_name
        ),
        wait_for_states = ["AVAILABLE", "TERMNINATING", "TERMINATED", "FAULTY", "UNKNOWN_ENUM_VALUE"]
    )

    return results

# end function update_volume_name()

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
