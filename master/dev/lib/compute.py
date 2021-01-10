import csv
import os
import os.path

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
            results = self.compute_client.list_images(
                compartment_id = self.compartment_id,
                sort_order = "ASC"
                ).data
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
    

    def __str__(self):
        return "Class setup to perform tasks against vm instance " + self.instance_name

# end class GetInstance

class LaunchVmInstance:
    
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
    compute_composite_client,
    instance_id):
    '''
    
    This function terminates a VM instance. The API will also destroy any boot 
    or block volumes associated with the instance. Your code must handle any 
    unexpected results. Your code must also handle any actions required prior
    to taking this action. THIS API WILL TERMINATE THE INSTANCE AND ALL ITS DATA,
    REGARDLESS OF THE RUNNING STATE OF THE INSTANCE OR THE PRESENCE OR LACK OF
    ANY BACKUPS.
    
    '''
    results = compute_composite_client.terminate_instance_and_wait_for_state(
        instance_id = instance_id,
        wait_for_states = ["TERMINATED"]).data
    return results

# end function terminate_instance()