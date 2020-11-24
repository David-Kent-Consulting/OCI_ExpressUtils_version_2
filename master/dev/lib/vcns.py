import oci

config = oci.config.from_file()
network_client = oci.core.VirtualNetworkClient(config)


class GetVirtualCloudNetworks:
    
    def __init__(self, compartment_id):
        self.compartment_id = compartment_id
        self.virtual_cloud_networks = []
        
    def __str__(self):
        return "This method initializes the class objects for GetVirtualNetworks"
    
    def populate_vcns(self):
        
        if len(self.virtual_cloud_networks) != 0:
            return None
        
        results = network_client.list_vcns(
            compartment_id = self.compartment_id
        )
        for item in results.data:
            if item.lifecycle_state != "TERMINATED":
                self.virtual_cloud_networks.append(item)