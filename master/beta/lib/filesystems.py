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

from time import sleep
import os.path

class GetExport:
    '''
    This class fetches and returns export data based on the methods called.
    Instiate it, then call the methods as appropriate. Exports do not require
    to reference availability zones, which makes the code logic simple.
    
    The coder should note that the entity relationship between the export,
    file system, and mount target are the export_id, file_system_id,
    and export_set_id. The export_set_id is equal to mount_target_id.
    '''
    
    def __init__(
        self,
        filesystem_client,
        compartment_id):
        
        self.filesystem_client = filesystem_client
        self.compartment_id = compartment_id
        self.exports = []
        
    def populate_exports(self):
        
        if len(self.exports) != 0:
            return None
        else:
            results = self.filesystem_client.list_exports(
                compartment_id = self.compartment_id
            ).data
            for export in results:
                if export.lifecycle_state not in ["DELETING", "DELETED"]:
                    self.exports.append(export)
            
    def return_all_exports(self):
        
        if len(self.exports) == 0:
            return None
        else:
            return self.exports
        
    def return_export(
        self,
        export_set_id):
        
        for exp in self.exports:
            if exp.export_set_id == export_set_id:
                export = self.filesystem_client.get_export(
                    export_id = exp.id
                ).data
                return export
    

# end class GetExport

class GetFileSystem:
    '''
    This class fetches and returns file system data based on the methods call.
    Your code passes to it the compartment_id, availability domains, and required OCI classes.
    Instiate, populate, and return your data as required by your code.
    
    The class must check each AD for file systems. Your code should call
    lib.general.get_availability_domains and then pass the object to this class.
    '''
    
    def __init__(
        self,
        filesystem_client,
        availability_domains,
        compartment_id):
        
        self.filesystem_client = filesystem_client
        self.availability_domains = availability_domains
        self.compartment_id = compartment_id
        self.filesystems = []
        
    def populate_file_systems(self):
        
        if len(self.filesystems) != 0:
            return None
        else:
            for AD in self.availability_domains:
                results = self.filesystem_client.list_file_systems(
                    compartment_id = self.compartment_id,
                    availability_domain = AD.name
                ).data
                # returned as a list which has a length of 0 if no filesystems found
                # we want to ignore results if empty
                if len(results) != 0:
                    for fs in results:
                        # only get stuff that is not in DELETED or DELETING state
                        if fs.lifecycle_state not in ["DELETED", "DELETING"]:
                            self.filesystems.append(fs)
                            
    def return_all_filesystems(self):
        
        if len(self.filesystems) == 0:
            return None
        else:
            return self.filesystems
    
    def return_filesystem(self, filesystem_name):
        
        if len(self.filesystems) == 0:
            return None
        else:
            for fs in self.filesystems:
                if fs.display_name == filesystem_name:
                    return fs

    def return_filesystem_using_id(self, file_system_id):

        if len(self.filesystems) == 0:
            return None
        else:
            for fs in self.filesystems:
                if fs.id == file_system_id:
                    return fs

    def __str__(self):
        
        return "class setup to fetch and return file system data from compartment " + self.compartment_id
    
# end class GetFileSystem

class GetMountTarget:
    '''
    This class fetches and returns mount target data based on the methods called.
    It follows similar convention as GetFileSystem. Coders should consult
    the code and comments in GetFileSystem prior to instiating this class.
    '''
    
    def __init__(
        self,
        filesystem_client,
        availability_domains,
        compartment_id):
        
        self.filesystem_client = filesystem_client
        self.availability_domains = availability_domains
        self.compartment_id = compartment_id
        self.mount_targets = []
        
    def populate_mount_targets(self):
        
        if len(self.mount_targets) != 0:
            return None
        else:
            for AD in self.availability_domains:
                results = self.filesystem_client.list_mount_targets(
                    compartment_id = self.compartment_id,
                    availability_domain = AD.name
                ).data
                if len(results) != 0:
                    for mt in results:
                        if mt.lifecycle_state not in ["DELETED", "DELETING"]:
                            self.mount_targets.append(mt)
    
    def return_all_mount_targets(self):
        
        if len(self.mount_targets) == 0:
            return None
        else:
            return self.mount_targets
    
    def return_mount_target(self, mount_target_name):
        
        if len(self.mount_targets) == 0:
            return None
        else:
            for mt in self.mount_targets:
                if mt.display_name == mount_target_name:
                    return mt
    
# end class GetMountTarget

def add_export_option(
    filesystem_client,
    UpdateExportDetails,
    ClientOptions,
    export,
    source,
    require_privileged_source_port,
    access,
    identity_squash,
    anonymous_uid,
    anonymous_gid,
    purge_with_addition
    ):
    '''
    This function adds an export record to export_options of the export.
    It expects the full export resource object. This is required in order
    to parse down the exiting options list if purge_with_addition == False.
    Otherwise, it ignores the existing options list and creates a new list
    with the single entry supplied to the function. source is the only
    required var. The function will check for an existing source address.
    If a duplicate is found, the function will return None, otherwise
    it applies the update.
    
    All others may be null. Your code must handle all pre-reqs
    and error conditions.
    '''
    
    for expo in export.export_options:
        if expo.source == source and not purge_with_addition:
            return None

    export_options = []
    export_options = [
        ClientOptions(
            source = source,
            require_privileged_source_port = require_privileged_source_port,
            access = access,
            identity_squash = identity_squash,
            anonymous_uid = anonymous_uid,
            anonymous_gid = anonymous_gid
        )
    ]

    if len(export.export_options)  and not purge_with_addition > 0:
        for expo in export.export_options:
            export_options.append(expo)
    
    update_export_details = UpdateExportDetails(
        export_options = export_options
    )
    
    update_export_response = filesystem_client.update_export(
        export_id = export.id,
        update_export_details = update_export_details
    ).data
    
    return update_export_response

# end function add_export_option()

def create_export(
    filesystem_composite_client,
    ClientOptions,
    CreateExportDetails,
    export_set_id,
    file_system_id,
    path):
    '''
    This function creates an export. This is what glues together the file system
    resource to the mount target resource, and is essentially nothing more than
    a permission. Consider the file system resource as the gateway to object
    storage, the mount target as the emulator between the file system resource
    and the NFS client, and the export as the permission that allows an NFS
    client to mount the emulated NFS mount point. Creating these resources are
    fairly straight forward. Deleting them should be done in reverse order.
    See the ERD below.
    
                file_system_resource             mount_target_resource
                         .                                 .
                         .                                 .......
                         ===================================     .
                                          .                      .
                                          .                ip_address_resource
                                   export_resource               .
                                          .                      .
                                          ========================
                                                     .
                                                     .
                                                nfs_client
                                  
    As always, your code must handle all pre-reqs, name duplication avoidance,
    and exceptions. The function returns a REST API response on success, or
    None on failure. 
    
    Your code passes the export_set_id, the file_system_id, and path.
    
    WARNING! The REST API service could create a BIG security hole on creation.
    It applies a permision of world access from any IP address with the resource
    and read-only permissions when no source address is created. We like to breakup
    the code in small portions to reduce risk, and thus, we choose to separate
    the process of granting access to the export the console. We have to handle it
    this way in this release since the SDK lacks a method for retrieving export
    client options.
    
    Fortunately, settin the source access permission to the loopback interface is 
    permitted. So this is what we choose to do, which essentially grants access
    to nothing.
    
    See the doclink below for explaination:
    https://docs.oracle.com/en-us/iaas/tools/python-sdk-examples/2.30.0/filestorage/create_export.py.html 
    '''
    
    create_export_details = CreateExportDetails(
        export_set_id = export_set_id,
        file_system_id = file_system_id,
        path = path,
        export_options = [
            ClientOptions(
                source = "127.0.0.1/32",
                access = "READ_ONLY"
            )
        ]
    )
    
    create_export_response = filesystem_composite_client.create_export_and_wait_for_state(
        create_export_details = create_export_details,
        wait_for_states = ["ACTIVE", "DELETING", "DELETED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    if create_export_response is None:
        return None
    else:
        return create_export_response
    
# end function create_export()

def create_filesystem(
    filesystem_composite_client,
    CreateFileSystemDetails,
    availability_domain,
    compartment_id,
    display_name,
    ):
    '''
    This function creates a file system storage object in the specified compartment
    at the specified availability domain within the specified region. It returns
    the REST API response upon success or None on failure. Your code must handle
    all pre-reqs, avoid duplicates, and handle exceptions
    '''
    
    create_file_system_details = CreateFileSystemDetails(
        availability_domain = availability_domain,
        compartment_id = compartment_id,
        display_name = display_name
    )
    
    create_file_system_response = filesystem_composite_client.create_file_system_and_wait_for_state(  
        create_file_system_details = create_file_system_details,
        wait_for_states = ["ACTIVE", "DELETING", "DELETED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    if create_file_system_response is not None:
        return create_file_system_response
    else:
        return None
    
# end function create_filesystem()

def create_mount_target(
    filesystem_composite_client,
    CreateMountTargetDetails,
    availability_domain,
    compartment_id,
    display_name,
    hostname_label,
    subnet_id,
    ip_address):
    '''
    This function creates a mount target, which is basically an NFS file
    system gateway to object storage. Both the cloud admin and cloud architect
    must be concerned with storage costs for file system storage, which is
    10 times the cost of block and object storage. Generally speaking, we advise that
    use of file system storage be constrained to low content applications, and that
    BLOBS be used for native cloud apps, and block storage for IaaS applications.
    
    We recommend that the file system and mount target be created in the same
    availability domain. Undefined program behavior may result if this
    condition is not met.
    
    Your code must handle all pre-reqs, including duplicate name avoidance.
    
    The function returns the REST API response upon success, or None on failure.
    Your code must handle any exceptions.
    '''
    
    
    create_mount_target_details = CreateMountTargetDetails(
        availability_domain = availability_domain,
        compartment_id = compartment_id,
        display_name = display_name,
        hostname_label = hostname_label,
        ip_address = ip_address,
        subnet_id = subnet_id
    )
    
    create_mount_target_response = filesystem_composite_client.create_mount_target_and_wait_for_state(  
        create_mount_target_details = create_mount_target_details,
        wait_for_states = ["ACTIVE", "DELETING", "DELETED", "FAILED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    if create_mount_target_response is None:
        return None
    else:
        return create_mount_target_response

# end function create_mount_target()

def delete_export(
    filesystem_composite_client,
    export_id):
    '''
    This function deletes an export from a mount target and file system. It returns
    a REST API response on success, or None on failure. Your code must handle all
    pre-reqs and exceptions.
    '''
    
    export_delete_response = filesystem_composite_client.delete_export_and_wait_for_state(
        export_id = export_id,
        wait_for_states = ["DELETED", "UNKNOWN_ENUM_VALUE"]
    )
    
    if export_delete_response is None:
        return None
    else:
        return export_delete_response
    
# end function delete_export()

def delete_export_option(
    filesystem_client,
    UpdateExportDetails,
    ClientOptions,
    export,
    source):
    '''
    This function deletes an export options entry from the export.
    It expects the full export resource object. It starts by searching
    for the source address provided against export.export_options.source
    If the source address is not found, it returns None. Otherwise,
    it appends export_options with any source objects that do not match
    the source address (this could be zero matches). Then it applies the
    updated export options list to the export without the specified
    source record. If the export options entries are zero, it returns
    None.
    
    Your code must handle all pre-reqs and error conditions.
    '''
    
    if len(export.export_options) == 0:
        return None
    
    source_found = False
    for expo in export.export_options:
        if expo.source == source:
            source_found = True
    if not source_found:
        return None
    
    export_options = []
    for expo in export.export_options:
        if expo.source != source:
            export_options.append(expo)
    
    update_export_details = UpdateExportDetails(
        export_options = export_options
    )
    
    update_export_response = filesystem_client.update_export(
        export_id = export.id,
        update_export_details = update_export_details
    ).data
    
    return update_export_response

# end function delete_export_option()

def delete_filesystem(
    filesystem_composite_client,
    compartment_id,
    file_system_id):
    '''
    This function deletes the specified file system from the specified compartment.
    It returns a result on success, or None on failure. Your code
    must handle any exceptions.
    '''
    
    delete_file_system_response = filesystem_composite_client.delete_file_system_and_wait_for_state(
        file_system_id = file_system_id,
        wait_for_states = ["DELETED", "UNKNOWN_ENUM_VALUE"]
    )
    
    if delete_file_system_response is not None:
        return delete_file_system_response
    else:
        return None

# end function delete_filesystem()

def delete_mount_target(
    filesystem_composite_client,
    mount_target_id):
    '''
    This function deletes a mount target. Your code must handle all pre-reqs.
    The function returns a REST API response on success, or None on failure.
    '''
    
    delete_mount_target_response = filesystem_composite_client.delete_mount_target_and_wait_for_state(  
        mount_target_id = mount_target_id,
        wait_for_states = ["DELETED", "FAILED", "UNKNOWN_ENUM_VALUE"]
    )
    
    if delete_mount_target_response is None:
        return None
    else:
        return delete_mount_target_response
    
# end function delete_mount_target()

def rename_filesystem(
    filesystem_composite_client,
    UpdateFileSystemDetails,
    file_system_id,
    display_name):
    '''
    This function renames a file system. Your code must handle all pre-reqs,
    including duplicate name avoidance. It returns a REST API response upon
    success, or None on failure. Your code must handle all exceptions.
    '''
    
    update_file_system_details = UpdateFileSystemDetails(
        display_name = display_name
    )
    
    update_file_system_response = filesystem_composite_client.update_file_system_and_wait_for_state( 
        file_system_id = file_system_id,
        update_file_system_details = update_file_system_details,
        wait_for_states = ["ACTIVE", "DELETING", "DELETED", "UNKNOWN_ENUM_VALUE"]
    )
    
    if update_file_system_response is not None:
        return update_file_system_details
    else:
        return None
    
# end function rename_filesystem()

def rename_mount_target(
    filesystem_composite_client,
    UpdateMountTargetDetails,
    mount_target_id,
    display_name):
    '''
    This function renames a mount target. Your code must handle all pre-reqs,
    including duplicate name avoidance. The function returns the REST API response
    upon success, or None on failure. Your code must handle exceptions.
    '''
    
    update_mount_target_details = UpdateMountTargetDetails(
        display_name = display_name
    )
    
    update_mount_target_response = filesystem_composite_client.update_mount_target_and_wait_for_state(  
        mount_target_id = mount_target_id,
        update_mount_target_details = update_mount_target_details,
        wait_for_states = ["ACTIVE", "DELETING", "DELETED", "FAILED", "UNKNOWN_ENUM_VALUE"]
    )
    
    if update_mount_target_response is None:
        return None
    else:
        return update_mount_target_response

# end function rename_mount_target

