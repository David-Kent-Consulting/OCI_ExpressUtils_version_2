from oci.core import VirtualNetworkClient

class GetLocalPeeringGateway:

    def __init__(self,
                network_client,
                compartment_id,
                virtual_network_id,
                local_peering_gateway_name):

        self.network_client = network_client
        self.compartment_id = compartment_id
        self.virtual_network_id = virtual_network_id
        self.local_peering_gateway_name = local_peering_gateway_name
        self.local_peering_gateways = []

    def populate_local_peering_gateways(self):
        if len(self.local_peering_gateways) != 0:
            return None
        else:
            results = self.network_client.list_local_peering_gateways(
                compartment_id = self.compartment_id
            ).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED" or item.lifecycle_state != "TERMINATING":
                    self.local_peering_gateways.append(item)

    def return_all_local_peering_gateways(self):
        if len(self.local_peering_gateways) == 0:
            return None
        else:
            return self.local_peering_gateways

    def return_local_peering_gateway(self):
        if len(self.local_peering_gateways) == 0:
            return None
        else:
            for item in self.local_peering_gateways:
                if item.display_name == self.local_peering_gateway_name:
                    return item

    def __str__(self):
        return "Method setup to perform tasks on " + self.local_peering_gateway_name

# end class GetLocalPeeringGateway

def create_local_peering_gateway_details(CreateLocalPeeringGatewayDetails,
                                         compartment_id,
                                         display_name,
                                         route_table_id,
                                         vcn_id):
    results = CreateLocalPeeringGatewayDetails(
        compartment_id = compartment_id,
        display_name = display_name,
        route_table_id = route_table_id,
        vcn_id = vcn_id
    )
    if results is not None:
        return results
    else:
        return None

# end function create_local_peering_gateway_details()

def add_local_peering_gateway(network_client, local_peering_gateway_details):
    
    results = network_client.create_local_peering_gateway(
        create_local_peering_gateway_details = local_peering_gateway_details
    )
    
    if results is not None:
        return results
    else:
        return None

# end function add_local_peering_gateway()

def create_lpg_peering(
    network_client,
    ConnectLocalPeeringGatewaysDetails,
    local_peering_gateway_id,
    remote_lpg_id):

    connect_local_peering_gateways_details = ConnectLocalPeeringGatewaysDetails(
        peer_id = remote_lpg_id)
    
    results = network_client.connect_local_peering_gateways(
        local_peering_gateway_id,
        connect_local_peering_gateways_details
    )

    if results is not None:
        return results
    else:
        return None

def delete_local_peering_gateway(network_client, local_peering_gateway_id):
    results = network_client.delete_local_peering_gateway(
        local_peering_gateway_id
    )
    if results is not None:
        return results
    else:
        return None

# end function delete_local_peering_gateway()