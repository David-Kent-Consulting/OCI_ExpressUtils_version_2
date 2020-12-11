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
    description,
    destination_type,
    destination,
    network_entity_id):

    results = RouteRule(
        description = description,
        destination_type = destination_type,
        destination = destination,
        network_entity_id = network_entity_id
    )

    return results

# end function define_route_rule

def add_route_table_rule(
    network_client,
    UpdateRouteTableDetails,
    route_table_id,
    route_rule
    ):
    
    # get the existing route table
    returned_route_rules = network_client.get_route_table(route_table_id)
    # append to empty list just the route rules from the object
    route_rules = []
    route_rules = returned_route_rules.data.route_rules
    route_rules.append(route_rule)
    # create the router details object
    route_table_details = UpdateRouteTableDetails(
        route_rules = route_rules
    )
    # Update the route table with the new route table entries
    # This must be done with all route rules at once.
    results = network_client.update_route_table(
        rt_id = route_table_id,
        update_route_table_details = route_table_details
    ).data

    if results is not None:
        return results
    else:
        return None

# end function add_route_table_rule()

def delete_route_rule(
    network_client,
    UpdateRouteTableDetails,
    route_table_id,
    route_rule
    ):
    # get the existing route table
    returned_route_rules = network_client.get_route_table(route_table_id)
    route_rules = []
    route_rules = returned_route_rules.data.route_rules
    if len(route_rules) is None:
        return None # do nothing if the route table is empty
    cntr = 0
    # using the python pop method, remove the item from the list where
    # route_rule is equal to the actual rule in the list, then break
    rule_match = False # necessary for below logic
    for rule in route_rules:
        if rule == route_rule:
            route_rules.pop(cntr)
            rule_match = True
            break
        cntr +=1

    # Only apply the rule if we got a match and removed a rule, otherwise
    # return None. The calling code will have to handle this condition as
    # a failure to apply the change due to the logic not having found a
    # rule to remove.
    if rule_match: 
        # create the router details object
        route_table_details = UpdateRouteTableDetails(
            route_rules = route_rules
        )

        # The reduced list of route rules will now be applied to the route table.
        results = network_client.update_route_table(
            rt_id = route_table_id,
            update_route_table_details = route_table_details
        ).data

        if results is None:
            # We want to abort if we are unable to apply the route change. This is to distinguish this
            # type of error from a condition where the route table rule could not be found.
            raise RuntimeError("EXCEPTION! - Route change could not be applied due to an unknown error\n")
        else:
            return results
    else:
        return None

# end function delete_route_rule()

def modify_route_table(
    network_client,
    UpdateRouteTableDetails,
    route_table_id,
    current_route_rule,
    replacement_route_rule
    ):

    # get the existing route table
    returned_route_rules = network_client.get_route_table(route_table_id)
    route_rules = []
    route_rules = returned_route_rules.data.route_rules
    if len(route_rules) is None:
        return None # do nothing if the route table is empty
    
    # Now we will search for current_route_rule, if found, we will modify the entry in the list, otherwise
    # we will return None. The calling code would have to handle the error if the route rule is not found.
    cntr = 0
    rule_match = False
    for rule in route_rules:
        if rule == current_route_rule:
            route_rules[cntr] = replacement_route_rule
            rule_match = True
            break
        cntr += 1

    if rule_match:
        # create the router details object
        route_table_details = UpdateRouteTableDetails(
            route_rules = route_rules
        )
        
        # The modified list of route rules will now be applied to the route table.
        results = network_client.update_route_table(
            rt_id = route_table_id,
            update_route_table_details = route_table_details
        ).data

        if results is None:
            # We want to abort if we are unable to apply the route change. This is to distinguish this
            # type of error from a condition where the route table rule could not be found.
            raise RuntimeError("EXCEPTION! - Route change could not be applied due to an unknown error\n")
        else:
            return results
    else:
        return None

# end function modify_route_table()