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
    network_client,
    drg_attachment_id):
    
    results = network_client.delete_drg_attachment(
        drg_attachment_id = drg_attachment_id)
    
    return results

# end function delete_drg_attachment