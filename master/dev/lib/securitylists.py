from oci.core import VirtualNetworkClient

class GetNetworkSecurityList:
    
    def __init__(self, network_client, compartment_id, vcn_id, security_list_name):
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.security_list_name = security_list_name
        self.security_lists = []

    def populate_security_lists(self):
        if len(self.security_lists) != 0:
            return None
        else:
            results = self.network_client.list_security_lists(
                self.compartment_id
            ).data

            for item in results:
                if item.lifecycle_state != "TERMINATED" or item.lifecycle_state != "TERMINATING":
                    self.security_lists.append(item)

    def return_all_security_lists(self):
        if len(self.security_lists) == 0:
            return None
        else:
            return self.security_lists

    def return_security_list(self):
        if len(self.security_lists) == 0:
            return None
        else:
            for item in self.security_lists:
                if item.display_name == self.security_list_name:
                    return item

    def __str__(self):
        return "Method setup for performing tasks against " + self.security_list_name

# end class GetNetworkSecurityList

def add__security_list(network_client, security_list_details):
    results = network_client.create_security_list(
        create_security_list_details = security_list_details
    ).data
    return results

# end function add_security_list()

def delete_security_list(network_client, security_list_id):
    results = network_client.delete_security_list(
        security_list_id
    )
    return results

# end function delete_security_list