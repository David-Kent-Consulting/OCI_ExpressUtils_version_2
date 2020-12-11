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
                                         vcn_id):
    # this function creates an object from the OCI API that is passed to
    # create_local_peering_gateway
    results = CreateLocalPeeringGatewayDetails(
        compartment_id = compartment_id,
        display_name = display_name,
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
        return results # results in this case is an OCI object of type None
    else:
        return None

# end function add_local_peering_gateway()

def create_lpg_peering(
    network_client,
    ConnectLocalPeeringGatewaysDetails,
    local_peering_gateway_id,
    remote_lpg_id):

    # Since we are creating a peer, all we need is the remote LPG OCID
    connect_local_peering_gateways_details = ConnectLocalPeeringGatewaysDetails(
        peer_id = remote_lpg_id)
    
    results = network_client.connect_local_peering_gateways(
        local_peering_gateway_id,
        connect_local_peering_gateways_details
    )

    if results is not None:
        return results # return type is an OCI object of type None
    else:
        return None

def delete_local_peering_gateway(network_client, local_peering_gateway_id):
    results = network_client.delete_local_peering_gateway(
        local_peering_gateway_id
    )
    if results is not None:
        return results # return type is an OCI object of type None
    else:
        return None

# end function delete_local_peering_gateway()

class GetNatGateway:
    
    def __init__(
        self,
        network_client,
        compartment_id,
        nat_gateway_name):

        self.network_client = network_client
        self.compartment_id = compartment_id
        self.nat_gateway_name = nat_gateway_name
        self.nat_gateways = []
    
    def populate_nat_gateways(self):
        if len(self.nat_gateways) != 0:
            return None
        else:
            results = self.network_client.list_nat_gateways(
                self.compartment_id
            ).data
            # the API is TFUBAR, it returns each object as a list of a single object,
            # which is poor programming since it is inconsistent with other APIs that
            # do similar things. Since there can by default only be one NGW per compartment
            # within a given region, we opt to:
            # 1) Not build a function that returns all NAT gateways in a compartment
            # 2) Handle returning the NGW as index 0 in the list.
            #
            # Thanks Oracle, this was really stupid!
            for nat_gateway in results:
                if nat_gateway.lifecycle_state != "TERMINATED" or nat_gateway.lifecycle_state != "TERMINATING)":
                    self.nat_gateways.append(results)
                    
    def return_nat_gateway(self):
        if len(self.nat_gateways) == 0:
            return None
        else:
            # Yep, here is how we have to handle the moron API from Oracle
            return self.nat_gateways[0][0]
        
    def __str__(self):
        return "Method setup to perform tasks on " + self.nat_gateway_name
    
# end class GetLocalPeeringGateway

def add_nat_gateway(
    network_client,
    CreateNatGatewayDetails,
    compartment_id,
    virtual_network_id,
    nat_gateway_name
    ):

    nat_gateway_details = CreateNatGatewayDetails(
        compartment_id = compartment_id,
        display_name = nat_gateway_name,
        vcn_id = virtual_network_id
    )
    
    results = network_client.create_nat_gateway(
        nat_gateway_details
    ).data

    if results is not None:
        return results
    else:
        return None

# end function add_nat_gateway

def delete_nat_gateway(
    network_client,
    nat_gateway_id
    ):
    
    results = network_client.delete_nat_gateway(
        nat_gateway_id = nat_gateway_id
    )
    if results is not None:
        return results
# end function delete_nat_gateway()