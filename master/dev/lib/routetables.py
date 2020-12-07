from oci.core import VirtualNetworkClient
from oci.core.models import RouteRule
from oci.core.models import CreateRouteTableDetails


class GetRouteTable:
    def __init__(self, network_client, compartment_id, vcn_id, route_table_name):
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.route_table_name = route_table_name
        self.route_tables = []

    def populate_route_tables(self):
        if len(self.route_tables) != 0:
            return None
        results = self.network_client.list_route_tables(self.compartment_id).data
        
        for item in results:
            if item.lifecycle_state != "TERMINATED" or item.lifecycle_state != "TERMINATING":
                self.route_tables.append(item)

    def return_all_route_tables(self):
        if len(self.route_tables) == 0:
            return None
        else:
            return self.route_tables

    def return_route_table(self):
        if len(self.route_tables) == 0:
            return None
        else:
            for item in self.route_tables:
                if item.display_name == self.route_table_name:
                    return item
    
    def ___str__(self):
        return "Method setup for performaing tasks against" + self.route_table_name

# end class GetSecurityList

def delete_route_table(
    network_client,
    route_table_id):

    results = network_client.delete_route_table(
        route_table_id
    )
    return results

# end function delete_route_table()

def add_route_table(
    network_client,
    create_route_table_details):

    results = network_client.create_route_table(
        create_route_table_details = create_route_table_details
    ).data

    return results

# end function add_route_table()

def define_route_rule(
    RouteRule,
    destination_type,
    destination,
    network_entity_id):

    results = RouteRule(
        destination_type = destination_type,
        destination = destination,
        network_entity_id = network_entity_id
    )

    return results