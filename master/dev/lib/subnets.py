from oci.core import VirtualNetworkClient
from oci.core.models import CreateSubnetDetails

class GetDhcpOptions:
    
    def __init__(self,
                 network_client,
                 compartment_id,
                 vcn_id,
                 dhcp_options_name):
        
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.dhcp_options_name = dhcp_options_name
        self.dhcp_options_resources = []
        
    def populate_dhcp_options(self):
        if len(self.dhcp_options_resources) != 0:
            return None
        else:
            results = self.network_client.list_dhcp_options(
                compartment_id = self.compartment_id
            ).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED" or item.lifecycle_state != "TERMINATING":
                    self.dhcp_options_resources.append(item)
    
    def return_all_dhcp_resources(self):
        if len(self.dhcp_options_resources) == 0:
            return None
        else:
            return self.dhcp_options_resources
    
    def return_dhcp_options_resource(self):
        if len(self.dhcp_options_resources) == 0:
            return None
        else:
            for item in self.dhcp_options_resources:
                if item.display_name == self.dhcp_options_name:
                    return item
    
    def __str__(self):
        return "Method setup to perform tasks on " + self.dhcp_options_name

# end class GetDhcpOptions

class GetPrivateIP:
    '''
    This class fetches and returns data about private IP addresses assigned to a subnet. Your code
    must handle all pre-reqs and exceptions. The method populate_ip_addresses() populates
    the class with IP address records. The method return_ip_by_address() accepts a string
    value representation of the IP address and returns that record if found. The method
    return_ip_by_ocid() accepts the ID of an IP address resource and returns that record
    if found.
    '''

    def __init__(
        self,
        network_client,
        subnet_id):

        self.network_client = network_client
        self.subnet_id = subnet_id
        self.ip_addresses = []

    def populate_ip_addresses(self):
        
        if len(self.ip_addresses) != 0:
            return None
        else:
            results = self.network_client.list_private_ips(
                subnet_id = self.subnet_id
            ).data
            for ip in results:
                self.ip_addresses.append(ip)
                
    def return_all_ip_addresses(self):
        
        if len(self.ip_addresses) == 0:
            return None
        else:
            return self.ip_addresses
    
    def return_ip_by_address(self, ip_address):
        
        if len(self.ip_addresses) == 0:
            return None
        else:
            for ip in self.ip_addresses:
                if ip.ip_address == ip_address:
                    return ip
                
    def return_ip_by_ocid(self, ip_address_id):
        
        if len(self.ip_addresses) == 0:
            return None
        else:
            for ip in self.ip_addresses:
                if ip.id == ip_address_id:
                    return ip
                
    def __str__(self):
        return "class setup to return private IP address data from subnet " + self.subnet_id
    
# end class GetPrivateIP

class GetSubnet:
    
    def __init__(self, network_client, compartment_id, vcn_id, subnet_name):
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.subnet_name = subnet_name
        self.subnets = []
    
    def populate_subnets(self):
        if len(self.subnets) != 0:
            return None
        else:
            results = self.network_client.list_subnets(
                compartment_id = self.compartment_id,
                vcn_id = self.vcn_id
            ).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED":
                    if item.lifecycle_state != "TERMINATING":
                        self.subnets.append(item)
    
    def return_all_subnets(self):
        if len(self.subnets) == 0:
            return None
        else:
            return self.subnets
    
    def return_subnet(self):
        if len(self.subnets) == 0:
            return None
        else:
            for item in self.subnets:
                if item.display_name == self.subnet_name:
                    return item
            
    def __str__(self):
        return "Method setup for performing tasks against " + self.subnet_name

# end class GetSubnet

def add_subnet(
    network_client,
    cidr_block,
    compartment_id,
    display_name,
    dns_label,
    prohibit_public_ip_on_vnic,
    route_table_id,
    security_list_ids,
    vcn_id
    ):
    
    # This OCI method is passed to create_subnet
    subnet_details = CreateSubnetDetails(
        compartment_id = compartment_id,
        cidr_block = cidr_block,
        display_name = display_name,
        dns_label = dns_label,
        prohibit_public_ip_on_vnic = prohibit_public_ip_on_vnic,
        route_table_id = route_table_id,
        security_list_ids = [security_list_ids],
        vcn_id = vcn_id
    )
    # print(subnet_details)
    
    results = network_client.create_subnet(
        create_subnet_details = subnet_details
    ).data

    # Your code must handle the exception if return type is None
    if results is not None:
        return results
    else:
        return None
# end function add_subnets()

def delete_subnet(
    network_client,
    subnet_id
    ):
    results = network_client.delete_subnet(subnet_id)
    return results
# end function delete_subnet()