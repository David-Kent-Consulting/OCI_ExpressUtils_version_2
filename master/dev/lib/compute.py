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

import csv
import os
import os.path


class GetCapacityReservations:
    
    def __init__(
        self,
        compute_client,
        compartment_id):

        self.compute_client     = compute_client
        self.compartment_id     = compartment_id
        self.reservation_list   = [] # thiis is where we will save the reservation list

    def populate_capacity_list(self):

        if len(self.reservation_list) !=0:
            return None
        
        else:
            capacity_response = self.compute_client.list_compute_capacity_reservations(
                compartment_id      = self.compartment_id
            )
            results = capacity_response.data
            if len(results) > 0:
                for cap in results:
                    if cap.lifecycle_state in ["ACTIVE", "CREATING", "UPDATING", "MOVING"]:
                        self.reservation_list.append(cap)
                while capacity_response.has_next_page:
                    capacity_response = self.compute_client.list_compute_capacity_reservations(
                    compartment_id      = self.compartment_id
                    )
                    capacity_response = results.data
                    for cap in results:
                        if cap.lifecycle_state in ["ACTIVE", "CREATING", "UPDATING", "MOVING"]:
                            self.reservation_list.append(cap)
    
    def return_all_capacity_reservations(self):
        if len(self.reservation_list) > 0:
            return self.reservation_list
        else:
            return None
        
    def return_capacity_reservation_name(self, cap_name):
        for res in self.reservation_list:
            if res.display_name == cap_name:
                return res
        return None
            

class GetImages:
    
    def __init__(
        self,
        compute_client,
        compartment_id):
        
        self.compute_client = compute_client
        self.compartment_id = compartment_id
        self.image_list = []    # here we will store a list of lists containing the
                                # display_name and image_id objects to save on memory
            
    def populate_image_list(self):

        if len(self.image_list) != 0:
            return None
        else:
            image_response = self.compute_client.list_images(
                compartment_id = self.compartment_id,
                sort_order = "ASC",
                lifecycle_state = "AVAILABLE"
                )
            results = image_response.data
            if len(results) > 0:
                for image in results:
                    temp_value = [image.display_name, image.id]
                    self.image_list.append(temp_value)
            while image_response.has_next_page:
                image_response = self.compute_client.list_images(
                    compartment_id = self.compartment_id,
                    sort_order = "ASC",
                    lifecycle_state = "AVAILABLE",
                    page = image_response.next_page
                )
                results = image_response.data
                if len(results) > 0:
                    for image in results:
                        temp_value = [image.display_name, image.id]
                        self.image_list.append(temp_value)
            
                    
    def return_image(self, image_name):

        if len(self.image_list) == 0:
            return None
        else:
            for image in self.image_list:
                if image[0] == image_name:
                    results = self.compute_client.get_image(
                        image_id = image[1]
                    ).data
                    if results.lifecycle_state == "AVAILABLE":
                        return results
            return None
    
    def search_for_image(self, search_string):

        if len(self.image_list) == 0:
            return None
        else:
            image_list = [] # we'll store the results here if we find anything
            for image in self.image_list:
                # return len(self.image_list[0][0])
                if search_string.upper() in image[0].upper():
                    image_list.append(image)
            if len(image_list) == 0:
                return None
            else:
                return image_list
    
    def __str__(self):
        return "Class setup to perform tasks for images in compartment id " + self.compartment_id

# end class GetImages

class GetInstance:
    
    def __init__(
        self,
        compute_client,
        compartment_id,
        instance_name):
        
        self.compute_client             = compute_client
        self.compartment_id             = compartment_id
        self.instance_name              = instance_name
        self.instance_list              = []
        
    def populate_instances(self):

        if len(self.instance_list) != 0:
            return None
        else:
            results = self.compute_client.list_instances(
                compartment_id = self.compartment_id).data
            for instance in results:
                if instance.lifecycle_state != "TERMINATED":
                    # had to nest the logic, using and did not work due to an unknown cause.
                    if instance.lifecycle_state != "TERMINATING":
                        self.instance_list.append(instance)

    def return_all_instances(self):

        if len(self.instance_list) == 0:
            return None
        else:
            return self.instance_list
    
    def return_instance(self):

        if self.instance_list == 0:
            return None
        else:
            for instance in self.instance_list:
                if instance.display_name == self.instance_name:
                    return instance
    
    def start_instance(self):

        if len(self.instance_list) == 0:
            return None
        else:
            for instance in self.instance_list:
                if instance.display_name == self.instance_name and instance.lifecycle_state == "STOPPED":
                    results = self.compute_client.instance_action(
                        instance_id = instance.id,
                        action = "START"
                    ).data
                    return results
            return None

    def hard_stop_instance(self):

        if len(self.instance_list) == 0:
            return None
        else:
            for instance in self.instance_list:
                if instance.display_name == self.instance_name and instance.lifecycle_state == "RUNNING":
                    results = self.compute_client.instance_action(
                        instance_id = instance.id,
                        action = "STOP"
                    ).data
                    return results
            return None

    def update_vm_instance_state(
        self,
        instance_id):

        if len(self.instance_list) == 0:
            return None
        else:
            results = self.compute_client.get_instance(
                instance_id = instance_id
            ).data
            return results
    
    def __str__(self):
        return "Class setup to perform tasks against vm instance " + self.instance_name

# end class GetInstance

class GetShapes:
    '''
    This class fetches and returns data from the REST service for instance shapes.
    Instiate by passing the compartiment ID to the class.
    '''

    def __init__(
        self,
        compute_client,
        compartment_id):
        
        self.compute_client = compute_client
        self.compartment_id = compartment_id
        self.shapes = []

    def populate_shapes(self):
        
        if len(self.shapes) != 0:
            return None
        else:
            list_shapes_response = self.compute_client.list_shapes(
                compartment_id = self.compartment_id
            )
            results = list_shapes_response.data
            if len(results) > 0:
                for shape in results:
                    self.shapes.append(shape)
            while list_shapes_response.has_next_page:
                list_shapes_response = self.compute_client.list_shapes(
                    compartment_id = self.compartment_id,
                    page = list_shapes_response.next_page
                )
                results = list_shapes_response.data
                if len(results) > 0:
                    for shape in results:
                        self.shapes.append(shape)

    def return_all_shapes(self):
        my_shapes = []
        for s in self.shapes:
            my_shapes.append(s.shape)
        return my_shapes

# end class GetShapes



class GetVnicAttachment:
    '''
    This class fetches and returns data from the REST service for virtual network
    interfaces. Instiate by passing to the class the compute client and compartment_id.
    Call populate_vnics() to add all vnics to the class
    
    Call return_all_vnics() to return all vnic data stored within the class.
    
    Call return_vnic() and pass to it instance_id to return a specific list of
    vnics attached to instance_id. The method always returns a list value even if
    only 1 vnic is attached to instance_id.
    
    Your code must handle all pre-reqs and error conditions.
    '''
    
    def __init__(
        self,
        compute_client,
        compartment_id):
        
        self.compute_client = compute_client
        self.compartment_id = compartment_id
        self.vnics = []
        
    def populate_vnics(self):
        
        if len(self.vnics) != 0:
            return None
        else:
            results = self.compute_client.list_vnic_attachments(
                compartment_id = self.compartment_id
            ).data
            # OCI's housekeeping for VNICs is insane. We only care about attached VNICs. 
            for vnic in results:
                if vnic.lifecycle_state not in ["DETACHED"]:
                    self.vnics.append(vnic)
                    
    def return_all_vnics(self):
        
        if len(self.vnics) == 0:
            return None
        else:
            return self.vnics
        
    def return_vnic(self, instance_id):
        
        if len(self.vnics) == 0:
            return None
        else:
            my_vnics = [] # there may be more than 1 vnic attached to instance_id.
            for vnic in self.vnics:
                if vnic.instance_id == instance_id:
                    my_vnics.append(vnic)
            return my_vnics

    def __str__(self):
        return "Class setup to perform tasks in compartment " + self.compartment_id

# end class GetVnicAttachment

class LaunchVmInstance:
    '''
    This class is depreciated and will be de-supported in a future release. It is
    replaced by the function launch_instance contained within this library.
    '''
    
    def __init__(
        self,
        compute_composite_client,
        CreateVnicDetails,
        InstanceSourceDetails,
        InstanceSourceViaImageDetails,
        LaunchInstanceDetails,
        LaunchInstanceShapeConfigDetails,
        compartment_id,
        subnet_id,
        host_details
        ):
        '''
        
        This class launches a VM using version 2.24.0 or later of the OCI API.
        It has been tested with Python version 3.8.5. Earlier versions of
        Python 3.x may result in undefined program behavior. It is not compatible
        with Python versions 2.x or earlier.
        
        Yhe methods only support launching an IaaS instance shape type of Flex, 
        and it does not use any depreciated API hooks. It uses the composite API
        so as to wait for either a successful or failed state upon completion of 
        the operation.
        
        Your code must check for duplicates since neither the class or API
        will do this. Your code must handle all exceptions.
        
        Besides loading the OCI APIs, the compartment ID, subnet ID, and host details
        must be provided. The format of the host_details dictionary object must be
        correct.
        
        Usage is straight forward. Begin by instiating the class as in the example below:
        
            launch_vm_instance = LaunchVmInstance(
                compute_composite_client,
                CreateVnicDetails,
                InstanceSourceDetails,
                InstanceSourceViaImageDetails,
                LaunchInstanceDetails,
                LaunchInstanceShapeConfigDetails,
                child_compartment.id,
                subnet.id,
                host_details)
                
        Next, run through each action as explained below for each method. Again, your code
        must handle any exceptions. Please check the values the methods store in the class
        prior to moving onto the next step.
        
        After instiating the class, build the VNIC method.
            launch_vm_instance.build_vnic_details()
            
        Next, build the shape method.
            launch_vm_instance.build_shape()
            
        Now, build the image details method.
            launch_vm_instance.build_instance_image_details()
        
        Now, put it all together and build the method for launching the IaaS instance.
            launch_vm_instance.build_launch_instance_details()
            
        It is important to ensure no errors in any of the preceeding steps prior to
        launching the instance, shown below.
            launch_vm_instance.launch_instance_and_wait_for_state()
            
        The latter method returns a REST API object that represents the state of the
        IaaS instance. Your code has to manage what happens after the instance has
        successfully entered a provisioning state or has entered a failed state.
        
        '''

        self.host_details = host_details
        # only read the ssh public key file if the source image is not a Windows image
        # This var is set in the function return_host_record in the program
        # Oci-AddWindowsVMsFromCsvFile.py or should be set in any code that
        # calls this method if the image source is of type Windows.
        if "NOT_USED_FOR_WINDOWS_IMAGES" == self.host_details["instance_details"]["ssh_key_file"]:
            pass
        else:
        # first read the SSH key to an object, otherwise raise an error
            if os.path.exists(host_details["instance_details"]["ssh_key_file"]):
                file_path = host_details["instance_details"]["ssh_key_file"]
                with open(file_path, mode = "r") as ssh_file:
                    self.ssh_public_key = ssh_file.read()
            else:
                raise RuntimeWarning("WARNING! SSH public key file not found")
        # now instiate the remaining self objects
        self.compute_composite_client = compute_composite_client
        self.CreateVnicDetails = CreateVnicDetails
        self.InstanceSourceDetails = InstanceSourceDetails
        self.InstanceSourceViaImageDetails = InstanceSourceViaImageDetails
        self.LaunchInstanceDetails = LaunchInstanceDetails
        self.LaunchInstanceShapeConfigDetails = LaunchInstanceShapeConfigDetails
        self.compartment_id = compartment_id
        self.subnet_id = subnet_id
        # the following to be instiated by calling the methods
        self.instance_source_via_image_details = None
        self.launch_instance_details = None
        self.shape_config = None
        self.vnic_details = None

    def build_vnic_details(self):
        
        self.vnic_details = self.CreateVnicDetails(
            assign_public_ip = self.host_details["network_properties"]["assign_public_ip"],
            display_name = self.host_details["network_properties"]["display_name"],
            hostname_label = self.host_details["instance_name"],
            private_ip = self.host_details["network_properties"]["private_ip"],
            subnet_id = self.subnet_id)
        
    def build_shape(self):
        
        # We only set the value of shape_config if the image type is not Windows
        if "NOT_USED_FOR_WINDOWS_IMAGES" != self.host_details["instance_details"]["ssh_key_file"]:
            self.shape_config = self.LaunchInstanceShapeConfigDetails(
                memory_in_gbs = self.host_details["shape_properties"]["memory_in_gbs"],
                ocpus = self.host_details["shape_properties"]["ocpus"])
        
    def build_instance_image_details(self):
        
        self.instance_source_via_image_details = self.InstanceSourceViaImageDetails(
            boot_volume_size_in_gbs = self.host_details["boot_volume_size_in_gbs"],
            image_id = self.host_details["image_id"])
        
    def build_launch_instance_details(self):

        # We only set the value of metadata if the image type is not Windows
        if "NOT_USED_FOR_WINDOWS_IMAGES" != self.host_details["instance_details"]["ssh_key_file"]:
            instance_metatdata = {
                "ssh_authorized_keys" : self.ssh_public_key
            }
            self.launch_instance_details = self.LaunchInstanceDetails(
                availability_domain = self.host_details["instance_details"]["availability_domain"],
                compartment_id = self.compartment_id,
                create_vnic_details = self.vnic_details,
                display_name = self.host_details["instance_name"],
                metadata = instance_metatdata,
                shape = self.host_details["shape_properties"]["shape"],
                shape_config = self.shape_config,
                source_details = self.instance_source_via_image_details)
        else:
            self.launch_instance_details = self.LaunchInstanceDetails(
                availability_domain = self.host_details["instance_details"]["availability_domain"],
                compartment_id = self.compartment_id,
                create_vnic_details = self.vnic_details,
                display_name = self.host_details["instance_name"],
                shape = self.host_details["shape_properties"]["shape"],
                shape_config = self.shape_config,
                source_details = self.instance_source_via_image_details)
        
    def launch_instance_and_wait_for_state(self):
        
        results = self.compute_composite_client.launch_instance_and_wait_for_state(
            launch_instance_details = self.launch_instance_details,
            wait_for_states = ["RUNNING", "UNKNOWN_ENUM_VALUE"]).data
        
        return results
        
    def __str__(self):
        return "Class setup to perform launch instance operations for " + self.host_details["instance_name"]

# end class LaunchVmInstance

class GetShapes:
    
    def __init__(
        self,
        compute_client,
        compartment_id):
        
        self.compute_client = compute_client
        self.compartment_id = compartment_id
        self.shapes = []
        
    def populate_shapes(self):
        
        if len(self.shapes) != 0:
            return None
        else:
            results = self.compute_client.list_shapes(
                compartment_id = self.compartment_id
            ).data
            
            self.shapes = results
            
    def return_all_shapes(self):

        if len(self.shapes) == None:
            return None
        else:
            return self.shapes
                
    def return_shape(self, shape_name):
        
        for shape in self.shapes:
            if shape.shape == shape_name:
                return shape

# end class GetShapes

def get_block_vol_attachments(
    compute_client,
    availability_domain_name,
    compartment_id,
    instance_id):
    '''
    This function returns all attached block volumes for a VM instance that are not
    in a terminated or terminating status. Your code must supply the availability
    domain in addition to the instance ID.
    
    Usage:
    
    my_results = get_block_vol_attachments(
        compute_client,
        availability_domain_name,
        compartment_id,
        instance_id)
    '''
    
    block_volumes = []
    
    results = compute_client.list_volume_attachments(
        availability_domain = availability_domain_name,
        compartment_id = compartment_id,
        instance_id = instance_id).data
    
    for block_volume in results:
        if block_volume.lifecycle_state != "DETACHED" and block_volume.lifecycle_state != "DETACHING":
            block_volumes.append(block_volume)
    
    return block_volumes

# end function get_block_vol_attachments

def get_boot_vol_attachments(
    compute_client,
    availability_domain_name,
    compartment_id,
    instance_id):
    '''
    This function returns all attached boot volumes for a VM instance that are not
    in a terminated or terminating status. Your code must supply the availability
    domain in addition to the instance ID.
    
    Usage:
    
    my_results = get_boot_vol_attachments(
        compute_client,
        availability_domain_name,
        compartment_id,
        instance_id)
    '''
    
    boot_volumes = []
    
    results = compute_client.list_boot_volume_attachments(
        availability_domain = availability_domain_name,
        compartment_id = compartment_id,
        instance_id = instance_id).data
    
    for boot_volume in results:
        if boot_volume.lifecycle_state != "TERMINATED" and boot_volume.lifecycle_state != "TERMINATING":
            boot_volumes.append(boot_volume)
    
    return boot_volumes

# end function get_boot_vol_attachments()

def change_instance_name(
    compute_client,
    UpdateInstanceDetails,
    instance,
    display_name):
    '''
    
    This fucntion will change the display name of a VM instance. It does not require that
    the instance be powered on. The instance object is returned upon completion.
    
    Your code must manage any exceptions.
    
    '''
    
    # instiate the instance details class
    update_instance_details = UpdateInstanceDetails(
        display_name = display_name)
    
    # Apply the change and return the results to the calling code
    results = compute_client.update_instance(
        instance_id = instance.id,
        update_instance_details = update_instance_details
    ).data
    
    return results

# end function change_instance_name()

def change_instance_shape(
    compute_composite_client,
    UpdateInstanceShapeConfigDetails,
    UpdateInstanceDetails,
    instance,
    shape,
    memory_in_gbs,
    ocpus):
    '''
    
    This function changes a VM instance shape. It is engineered to only use the newer
    API to change shapes using the Flex shapes. It will not process to the older API
    hook for legacy VM shapes. It will abort if a legacy shape is chosen. Your code must
    handle any warnings prior to application of the shape change. This function will
    result in the instance being rebooted by the OCI REST API service.
    
    '''
    if shape == "VM.Standard.E3.Flex":
        # Sets the FLEX shape details, see OCI documentation for valid shape configs
        shape_config = UpdateInstanceShapeConfigDetails(
            memory_in_gbs = memory_in_gbs,
            ocpus = ocpus)
        # Applies the shape config to the shape details class
        update_instance_details = UpdateInstanceDetails(
            shape = shape,
            shape_config = shape_config)
        
        # applies the change
        results = compute_composite_client.update_instance_and_wait_for_state(
            instance_id = instance.id,
            update_instance_details = update_instance_details,
            wait_for_states = ["RUNNING"]).data
        return results
        
    else:
        raise RuntimeWarning("WARNING! - Only FLEX shapes are supported by this utility.")

# end function change_instance_shape()
def check_for_vm(
    compute_client,
    compartment_id,
    vm_name):
    '''
    Function returns boolean True if the vm instance is found, otherwise it returns false
    '''
    vm_instances = GetInstance(
        compute_client,
        compartment_id,
        vm_name
    )
    vm_instances.populate_instances()
    vm_instance = vm_instances.return_instance()
    if vm_instance is not None:
        return True
    else:
        return False

# end function check_for_vm()

def get_vm_instance_response(
    compute_client,
    wait_until,
    instance_id,
    desired_state,
    wait_interval_in_seconds,
    max_wait_time_in_seconds):
    '''
    This function calls oci.wait_until for the lifecycle state desired_state within the
    timeframe max_wait_tim_in_seconds, and returns an OCI response upon success or failure
    of the desired state. It should be called by your code when you need to wait for a
    specific lifecycle state.

    See https://docs.oracle.com/en-us/iaas/tools/python/2.18.0/waiters.html for an explaination.
    '''
    
    get_instance_response = wait_until(
        compute_client,
        compute_client.get_instance(instance_id),
        "lifecycle_state",
        desired_state,
        max_interval_seconds = wait_interval_in_seconds,
        max_wait_seconds = max_wait_time_in_seconds)
    return get_instance_response

# end function get_vm_instance_response

def launch_instance(
    compute_composite_client,
    CreateVnicDetails,
    InstanceSourceDetails,
    InstanceSourceViaImageDetails,
    LaunchInstanceDetails,
    LaunchInstanceShapeConfigDetails,
    LaunchOptions,
    boot_volume_size_in_gbs,
    compartment_id,
    subnet_id,
    availability_domain,
    private_ip,
    display_name,
    shape,
    ocpus,
    memory_in_gbs,
    image_id,
    ssh_public_key
    ):
    
    '''
    
    The following could have been nested but is not for the purpose of simplifying readability of the code.
    
    '''
    
    # start by building the VNIC object
    create_vnic_details = CreateVnicDetails(
        assign_private_dns_record=True,
        assign_public_ip=False,
        display_name = display_name.upper() + "_vnic_00",
        hostname_label = display_name.lower(),
        private_ip = private_ip,
        subnet_id = subnet_id
    )
    
    # Create the launch_options object to pin the boot volume type to paravirtualized
    launch_options = LaunchOptions(
        boot_volume_type = "PARAVIRTUALIZED",
        network_type = "PARAVIRTUALIZED"
    )
    
    # build the shape_config object
    shape_config = LaunchInstanceShapeConfigDetails(
        ocpus = ocpus,
        memory_in_gbs = memory_in_gbs
    )
    
    # build the source_details object
    source_details = InstanceSourceViaImageDetails(
        boot_volume_size_in_gbs = boot_volume_size_in_gbs,
        source_type = "image",
        image_id = image_id
    )
    '''
    Now bring it together by creating the object launch_instance_details. Logic follows one of 2 paths:
    
    if ssh_key_file contains a valid string value, create launch_instance_details with instance_metadata
    with value for ssh_authorized_keys, otherwise logic creates launch_instance_details with an object
    value of type None
    object.
    
    '''
    
    if ssh_public_key is not None:
        '''
        It is possible that a Linux instance may be created from an image that does not require
        an SSH key. This is unlikely. The more likely scenario is that the instance being
        created is on Windows, in which case ssh_public_key should be passed as type
        None to the function. The REST API will process the instance create request
        even if the value of instance_metadata is None. Note the REST service will ignore
        a passed ssh key value when the source image is of OS type Windows.
        
        '''
        instance_metadata = {
            "ssh_authorized_keys" : ssh_public_key
        }
    else:
        instance_metadata = None

    
    launch_instance_details = LaunchInstanceDetails(
        availability_domain = availability_domain,
        compartment_id = compartment_id,
        shape = shape,
        create_vnic_details = create_vnic_details,
        display_name = display_name.upper(),
        hostname_label = display_name.lower(),
        metadata = instance_metadata,
        launch_options = launch_options,
        shape_config = shape_config,
        source_details = source_details
        )
    
    
    # create the instance
    launch_instance_response = compute_composite_client.launch_instance_and_wait_for_state(
        launch_instance_details = launch_instance_details,
        wait_for_states = ["RUNNING", "TERMINATING", "TERMINATED", "UNKNOWN_ENUM_VALUE"]
    )
    
    return launch_instance_response

# end function launch_Linux_instance

def launch_instance_from_boot_volume(
    compute_composite_client,
    LaunchInstanceDetails,
    CreateVnicDetails,
    LaunchOptions,
    InstanceSourceDetails,
    InstanceSourceViaBootVolumeDetails,
    availability_domain,
    compartment_id,
    shape,
    display_name,
    private_ip,
    subnet_id,
    shape_config,
    boot_volume_id
    ):

    launch_instance_details = LaunchInstanceDetails(
        availability_domain = availability_domain,
        compartment_id = compartment_id,
        shape = shape,
        create_vnic_details = CreateVnicDetails(
            assign_public_ip = False,
            display_name = display_name,
            hostname_label = display_name,
            private_ip = private_ip,
            subnet_id = subnet_id
        ),
        display_name = display_name,
        hostname_label = display_name,
        launch_options = LaunchOptions(
            boot_volume_type = "PARAVIRTUALIZED",
            network_type = "PARAVIRTUALIZED"
        ),
        shape_config = shape_config,
        source_details = InstanceSourceViaBootVolumeDetails(
            source_type = "bootVolume",
            boot_volume_id = boot_volume_id
        )
    )

    # return launch_instance_details

    launch_instance_from_boot_volume_response = compute_composite_client.launch_instance_and_wait_for_state(
        launch_instance_details = launch_instance_details,
        wait_for_states = ["RUNNING", "UNKNOWN_ENUM_VALUE", "TERMINATING", "TERMINATED"]
    )

    return launch_instance_from_boot_volume_response



# end function launch_instance_from_boot_volume

def reboot_os_and_instance(
    compute_composite_client,
    instance_id):
    '''

    This function gracefully shuts down a VM instance OS and then restarts the instance.
    The function will wait until the instance is in a RUNNING state and then returns
    the results to the calling code. Your code must handle any runtime errors or
    unexpected results.

    '''
    results = compute_composite_client.instance_action_and_wait_for_state(
        instance_id = instance_id,
        action = "SOFTRESET",
        wait_for_states = ["RUNNING", "STARTING", "STOPPED", "UNKNOWN_ENUM_VALUE"]).data
    return results

# end function reboot_os_and_instance()

def reboot_instance(
    compute_composite_client,
    instance_id):
    '''

    This function ungracefully shuts down a VM instance OS and then reboots the instance.
    The function will wait until the instance is in a RUNNINGF state and then returns
    the results to the calling code. Your code must handle any runtime errors or
    unexpected results.

    '''
    results = compute_composite_client.instance_action_and_wait_for_state(
        instance_id = instance_id,
        action = "RESET",
        wait_for_states = ["RUNNING", "STARTING", "STOPPED", "UNKNOWN_ENUM_VALUE"]).data
    return results

# end function reboot_instance()

def stop_os_and_instance(
    compute_composite_client,
    instance_id):
    '''

    This function gracefully shuts down a VM instance OS and then halts the instance.
    The function will wait until the instance is in a STOPPED state and then returns
    the results to the calling code. Your code must handle any runtime errors or
    unexpected results.

    '''
    results = compute_composite_client.instance_action_and_wait_for_state(
        instance_id = instance_id,
        action = "SOFTSTOP",
        wait_for_states = ["STOPPED"]).data
    return results

# end function stop_os_and_instance()

def terminate_instance(
    compute_client,
    compute_composite_client,
    instance_id,
    preserve_disks):
    '''
    
    This function terminates a VM instance. The API will also destroy any boot 
    or block volumes associated with the instance. Your code must handle any 
    unexpected results. Your code must also handle any actions required prior
    to taking this action. 
    IF PRESERVE_DISKS IS FALSE, THIS API WILL TERMINATE THE INSTANCE AND ALL ITS OS DATA,
    REGARDLESS OF THE RUNNING STATE OF THE INSTANCE OR THE PRESENCE OR LACK OF
    ANY BACKUPS. SET PRESERVE_DISKS TO TRUE TO TERMINATE THE VM INSTANCE AND LEAVE THE
    STORAGE IN PLACE.

    IMPORTANT! Your code MUST manage removal of data disk volumes.

    IMPORTANT! Your code must manage removing the disks from any backup policy if desired
    if you are leaving the disk volumes in place.
    
    '''
    if preserve_disks:
        results = compute_client.terminate_instance(
            instance_id = instance_id,
            preserve_boot_volume = True
        )

    else:
        results = compute_composite_client.terminate_instance_and_wait_for_state(
            instance_id = instance_id,
            wait_for_states = ["TERMINATED"]).data
        
    return results

# end function terminate_instance()


def update_instance_name(
    compute_client,
    UpdateInstanceDetails,
    instance_id,
    display_name
    ):
    
    instance_details = UpdateInstanceDetails(
        display_name = display_name
    )
    
    results = compute_client.update_instance(
        instance_id = instance_id,
        update_instance_details = instance_details
    ).data
    
    if results is not None:
        return results
    else:
        return None

# end function update_instance_name