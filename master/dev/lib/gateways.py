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
                if item.lifecycle_state != "TERMINATED":
                    if item.lifecycle_state != "TERMINATING":
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
        virtual_cloud_network_id,
        nat_gateway_name):

        self.network_client = network_client
        self.compartment_id = compartment_id
        self.virtual_cloud_network_id = virtual_cloud_network_id
        self.nat_gateway_name = nat_gateway_name
        self.nat_gateways = []
    
    def populate_nat_gateways(self):
        if len(self.nat_gateways) != 0:
            return None
        else:
            # We compensate for the shortfall in this API by specifying the vcn_id in our
            # call. This allows for the use of the API to list but be specific to the
            # VCN in which the NAT gateway was created within. So, if a client decides to
            # have more than 1 NAT gateway per compartment within the same region (aka not the
            # defaults) we can accommodate the condition without lots of code.
            results = self.network_client.list_nat_gateways(
                compartment_id = self.compartment_id,
                vcn_id = self.virtual_cloud_network_id

            ).data
            # the API is TFUBAR, it returns each object as a list of a single object,
            # which is poor programming since it is inconsistent with other APIs that
            # do similar things. Since there can by default only be one NGW per compartment
            # within a given region, we opt to:
            # 1) Not build a function that returns all NAT gateways in a compartment
            # 2) Handle returning the NGW as index 0 in the list.
            for nat_gateway in results:
                if nat_gateway.lifecycle_state != "TERMINATED":
                    if nat_gateway.lifecycle_state != "TERMINATING)":
                        self.nat_gateways.append(nat_gateway)
                    
    def return_nat_gateway(self):
        if len(self.nat_gateways) == 0:
            return None
        else:
            # Yep, here is how we have to handle the moron API from Oracle
            # return self.nat_gateways[0]
            count = len(self.nat_gateways)
            cntr = 0
            while cntr < count:
                if self.nat_gateways[cntr].display_name == self.nat_gateway_name:
                    return self.nat_gateways[cntr]
                cntr += 1
        
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

class GetInternetGateway:
    
    def __init__(
        self,
        network_client,
        compartment_id,
        virtual_cloud_network_id,
        internet_gateway_name):
    
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.virtual_cloud_network_id = virtual_cloud_network_id
        self.internet_gateway_name = internet_gateway_name
        self.internet_gateways = []
    
    def populate_internet_gateways(self):
        if len(self.internet_gateways) != 0:
            return None
        else:
            # We compensate for the shortfall in this API by specifying the vcn_id in our
            # call. This allows for the use of the API to list but be specific to the
            # VCN in which the internet gateway was created within. So, if a client decides to
            # have more than 1 internet gateway per compartment within the same region (aka not the
            # defaults) we can accommodate the condition without lots of code.
            results = self.network_client.list_internet_gateways(
                compartment_id = self.compartment_id
            ).data
            # the API is TFUBAR, it returns each object as a list of a single object,
            # which is poor programming since it is inconsistent with other APIs that
            # do similar things. Since there can by default only be one IGW per compartment
            # within a given region, we opt to:
            # 1) Not build a function that returns all NAT gateways in a compartment
            # 2) Handle returning the IGW as index 0 in the list.
            for internet_gateway in results:
                if internet_gateway.lifecycle_state != "TERMINATED":
                    if internet_gateway.lifecycle_state != "TERMINATING":
                        self.internet_gateways.append(internet_gateway)

        
    def return_internet_gateway(self):
        if len(self.internet_gateways) == 0:
            return None
        else:
            count = len(self.internet_gateways)
            cntr = 0
            while cntr < count:
                if self.internet_gateways[cntr].display_name == self.internet_gateway_name:
                    return self.internet_gateways[cntr]
                cntr += 1
#            return self.internet_gateways[0]
        
    def __str__(self):
        return "Method setup to perform tasks on " + self.internet_gateway_name

# end class GetInternetGateway

def delete_internet_gateway(
    network_client,
    internet_gateway_id
    ):

    results = network_client.delete_internet_gateway(
        ig_id = internet_gateway_id
    )
    if results is not None:
        # your code must handle exception if o object is returned. Such a condition would indicate that
        # the IGW had not been removed.
        return results

# end function delete_internet_gateway

def add_internet_gateway(
    network_client,
    CreateInternetGatewayDetails,
    compartment_id,
    virtual_network_id,
    internet_gateway_name
    ):

    # instiate the API method
    internet_gateway_details = CreateInternetGatewayDetails(
        compartment_id = compartment_id,
        display_name = internet_gateway_name,
        is_enabled = True,
        vcn_id = virtual_network_id
    )
    
    results = network_client.create_internet_gateway(
        create_internet_gateway_details = internet_gateway_details
    ).data

    if results is not None:
        return results
    else:
        return None

# end function  add_internet_gateway()

class GetDynamicRouterGateway:
    
    def __init__(
        self,
        network_client,
        compartment_id,
        dynamic_router_gateway_name):
        
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.dynamic_router_gateway_name = dynamic_router_gateway_name
        self.dynamic_router_gateways = []
        
    def populate_dynamic_router_gateways(self):
        if len(self.dynamic_router_gateways) != 0:
            return None
        else:
            results = self.network_client.list_drgs(
                compartment_id = self.compartment_id
            ).data
            for item in results:
                if item.lifecycle_state != "TERMINATED":
                    if item.lifecycle_state != "TERMINATING":
                        self.dynamic_router_gateways.append(item)
                    
    def return_dynamic_router_gateway(self):
        if len(self.dynamic_router_gateways) == 0:
            return None
        else:
            count = len(self.dynamic_router_gateways)
            cntr = 0
            while cntr < count:
                if (self.dynamic_router_gateways[cntr].display_name == self.dynamic_router_gateway_name):
                    return self.dynamic_router_gateways[cntr]
                cntr += 1
    
    def __str__(self):
        return "Method GetDynamicRouter setup to perform tasks against " + self.dynamic_router_gateway_name

def add_dynamic_router_gateway(
    network_client,
    CreateDrgDetails,
    compartment_id,
    dynamic_router_gateway_name
    ):
    
    dynamic_router_details = CreateDrgDetails(
        compartment_id = compartment_id,
        display_name = dynamic_router_gateway_name
    )
    
    results = network_client.create_drg(
        create_drg_details = dynamic_router_details
    ).data
    
    return results

# end function add_dynamic_router_gateway()

def delete_dynamic_router(
    network_client,
    dynamic_router_gateway_id
    ):
    
    results = network_client.delete_drg(
        drg_id = dynamic_router_gateway_id
    )
    
    return results

# end function delete_dynamic_router()

class GetDrgAttachment:
    
    def __init__(self,
             network_client,
             compartment_id,
             vcn_id,
             drg_attachment_name):
        
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.drg_attachment_name = drg_attachment_name
        self.drg_attachments = []
    
    def populate_drg_attachments(self):
        
        if len(self.drg_attachments) != 0:
            return None
        else:
            results = self.network_client.list_drg_attachments(
                compartment_id = self.compartment_id,
                vcn_id = self.vcn_id).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED":
                    if item.lifecycle_state != "TERMINATING":
                        self.drg_attachments.append(item)
                    
    def return_all_drg_attachments(self):
        if len(self.drg_attachments) == 0:
            return None
        else:
            return self.drg_attachments
    
    def return_drg_attachment(self):
        if len(self.drg_attachments) == 0:
            return None
        else:
            for item in self.drg_attachments:
                if item.display_name == self.drg_attachment_name:
                    return item
    
    def __str__(self):
        return "Method setup to perform tasks against " + self.drg_attachment_name

# end class GetDrgAttachment

def attach_drg_to_vcn(
    network_client,
    CreateDrgAttachmentDetails,
    display_name,
    drg_id,
    route_table_id,
    vcn_id):
    
    drg_attachment_details = CreateDrgAttachmentDetails(
        display_name = display_name,
        drg_id = drg_id,
        route_table_id = route_table_id,
        vcn_id = vcn_id)
    
    results = network_client.create_drg_attachment(
        create_drg_attachment_details = drg_attachment_details).data
    
    return results

# end function attach_drg_to_vcn()

def delete_drg_attachment(
    network_composite_client,
    drg_attachment_id):
    
    results = network_composite_client.delete_drg_attachment_and_wait_for_state(
        drg_attachment_id = drg_attachment_id,
        wait_for_states = ["DETACHED", "UNKNOWN_ENUM_VALUE"]
    )

    return results

# end function delete_drg_attachment

def update_local_peering_gateway_router(
    network_composite_client,
    UpdateLocalPeeringGatewayDetails,
    local_peering_gateway_id,
    route_table_id
    ):
    '''
    This function associates a route table with a local peering router, or replaces
    the current associated route table with the specified replacement route table.
    '''
    
    update_local_peering_gateway_response = network_composite_client.update_local_peering_gateway_and_wait_for_state( 
        local_peering_gateway_id = local_peering_gateway_id,
        update_local_peering_gateway_details = UpdateLocalPeeringGatewayDetails(
            route_table_id = route_table_id
        ),
        wait_for_states = ["AVAILABLE", "TERMINATED", "UNKNOWN_ENUM_VALUE"]
    ).data
    
    if update_local_peering_gateway_response is None:
        return None
    else:
        return update_local_peering_gateway_response
    
# end function update_local_peering_gateway_router()

class GetDrgPeeringConnection:
    '''
    This class fetches and returns data regarding DRG remote peering connections. Pass
    to the class your configured network_client class for the specified region along
    with compartment_id, then call populate_rpc_connections() to add the data to the
    class. return_all_rpc_connections() will return all found RPC connections in the
    compartment. This is possible since a DRG may have multiple connections. Call
    return_drg_connection() and provide the name of the connection, and it will return
    data just on that connection. Coders should note that the REST service response will
    also include the state of the peered connection, either as NEW, PEERED, REVKOKED, or
    transitional states.
    A connection that has been REVOKED cannot be connected to a new RPC. It must be
    terminated.
    '''
    
    def __init__(
        self,
        network_client,
        compartment_id):
        
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.rpc_connections = []
    
    def populate_rpc_connections(self):
        
        if len(self.rpc_connections) != 0:
            return None
        else:
            results = self.network_client.list_remote_peering_connections(
                compartment_id = self.compartment_id
            ).data
            
            for rpc in results:
                if rpc.lifecycle_state not in ["TERMINATING", "TERMINATED"]:
                    self.rpc_connections.append(rpc)
    
    def return_all_rpc_connections(self):
        
        if len(self.rpc_connections) == 0:
            return None
        else:
            return self.rpc_connections
        
    def return_rcp_connection(self, rpc_connection_name):
        
        if len(self.rpc_connections) == 0:
            return None
        else:
            for rpc in self.rpc_connections:
                if rpc.display_name == rpc_connection_name:
                    return rpc
                
    def __str__(self):
        return "Class setup to fetch and return RPC data from compartment " + self.compartment_id 
    
# end class GetDrgPeeringConnection

def create_drg_rpc(
    network_client,
    CreateRemotePeeringConnectionDetails,
    compartment_id,
    display_name,
    drg_id
    ):
    '''
    This function creates a DRG remote connection resource.
    
    Your code must handle all pre-reqs and error conditions. You must
    avoid name duplication in your code since OCI does not enforce
    this.
    
    You should also insert a 10 second wait after creating. The API 
    documentation claims to have a composite function for creating
    this resource but in fact does not.
    
    DRGs provider for inter-region and inter-tenancy connections. The DRGs must exist
    on either connection point and be attached to their respective VCNs. Next, create
    the DRG connection resource on both sides. Finally, establish the connection link
    using create_drg_rpc_connection().
    '''
    
    create_remote_peering_connection_details = CreateRemotePeeringConnectionDetails(
        compartment_id = compartment_id,
        display_name = display_name,
        drg_id = drg_id
    )
    
    create_remote_peering_connection_response = network_client.create_remote_peering_connection( 
        create_remote_peering_connection_details = create_remote_peering_connection_details
    ).data
    
    return create_remote_peering_connection_response

# end function create_drg_rpc

def create_drg_rpc_connection(
    network_client,
    ConnectRemotePeeringConnectionsDetails,
    remote_peering_connection_id,
    peer_id,
    peer_region_name):
    '''
    This function creates a remote peering connection between two DRGs. It should
    be used to establish routing between regions and/or tenancies. Your code must
    handle all pre-reqs and error conditions. You must provide the composite network
    client for the DRG connection source, the remote peering connection ID, and the
    remote region name.
    
    Your code must handle all pre-reqs and error conditions.
    '''
    
    connect_remote_peering_connections_details = ConnectRemotePeeringConnectionsDetails(
        peer_id = peer_id,
        peer_region_name = peer_region_name
    )
    
    connect_remote_peering_connections_response = network_client.connect_remote_peering_connections( 
        remote_peering_connection_id,
        connect_remote_peering_connections_details = connect_remote_peering_connections_details
    ).data
    
    return connect_remote_peering_connections_response

# end function create_drg_rpc_connection()

def delete_drg_rpc(
    network_composite_client,
    remote_peering_connection_id):
    '''
    This function deletes a dynamic router gateway's remote peering connection. It does
    not delete a remote peered connection. Your code musyt handle all pre-reqs related to
    properly removing an RPC on both sides when peered. The function returns a response
    upon successful execution of type oci.response.Response. The response holds data.
    
    We have found the REST API response time for deleting RPCs as poor as creating them.
    We use the composite client in this case since this part of the SDK is stable.
    '''
    
    delete_rcp_response = network_composite_client.delete_remote_peering_connection_and_wait_for_state(
        remote_peering_connection_id = remote_peering_connection_id,
        wait_for_states = ["TERMINATED", "UNKNOWN_ENUM_VALUE"]
    )
    
    return delete_rcp_response

# end function delete_drg_rpc()