from oci.core import VirtualNetworkClient

class GetNetworkSecurityGroup:
    
    def __init__(
        self,
        network_client,
        compartment_id,
        vcn_id,
        security_group_name):
        
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.security_group_name = security_group_name
        self.security_groups = []
        
    def populate_security_groups(self):
        if len(self.security_groups) != 0:
            return None
        else:
            results = self.network_client.list_network_security_groups(
                compartment_id = self.compartment_id,
                vcn_id = self.vcn_id).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED" or item.lifecycle_state != "TERMINATING":
                    self.security_groups.append(item)
                    

    def return_all_security_groups(self):
        if len(self.security_groups) == 0:
            return None
        else:
            return self.security_groups
        
    def return_security_group(self):
        if len(self.security_groups) == 0:
            return None
        else:
            for item in self.security_groups:
                if item.display_name == self.security_group_name:
                    return item
    
    def __str__(self):
        return "Method setup to perform tasks on " + self.security_group_name

# end class GetNetworkSecurityGroup

def add_security_group(
    network_client,
    CreateNetworkSecurityGroupDetails,
    compartment_id,
    vcn_id,
    security_group_name):
    
    security_group_details = CreateNetworkSecurityGroupDetails(
        compartment_id = compartment_id,
        display_name = security_group_name,
        vcn_id = vcn_id)
    
    results = network_client.create_network_security_group(
        create_network_security_group_details = security_group_details).data
    
    return results

# end function GetNetworkSecurityGroup()

def delete_security_group(
    network_client,
    network_security_group_id):
    
    results = network_client.delete_network_security_group(
        network_security_group_id = network_security_group_id)
    
    return results

# end function delete_security_group()