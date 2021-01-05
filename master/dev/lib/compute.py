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
        compute_composite_client,
        compartment_id,
        instance_name):
        
        self.compute_client             = compute_client
        self.compartment_id             = compartment_id
        self.compute_composite_client   = compute_composite_client,
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
    instance):
    '''
    
    This function terminates a VM instance. It starts by checking the lifecycle state of
    the instance. If the state is not "STOPPED", it raises a RuntimeWarning. Otherwise,
    it terminates the instance. The API will also destroy any boot or block volumes
    associated with the instance. Your code must handle any unexpected results.
    
    '''
    if instance.lifecycle_state != "STOPPED":
        raise RuntimeWarning("WARNING! Instance must be fully stopped to terminate.")
    else:
        results = compute_composite_client.terminate_instance_and_wait_for_state(
            instance_id = instance.id,
            wait_for_states = ["TERMINATED"]).data
        return results

# end function terminate_instance()

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