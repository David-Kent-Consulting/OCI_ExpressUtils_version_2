# Copyright 2019 – 2022 David Kent Consulting, Inc.
# All Rights Reserved.
# 
# NOTICE:  All information contained herein is, and remains
# the property of David Kent Consulting, Inc.; David Kent Cloud Solutions, Inc.;
# and its affiliates (The Company). The intellectual and technical concepts contained
# herein are proprietary to The Company and may be covered by U.S. and Foreign Patents,
# patents in process, and are protected by trade secret or copyright law.
# Dissemination of this information or reproduction of this material
# is strictly forbidden unless prior written permission is obtained
# from The Company.
#
# This file is subject to the terms and conditions defined in
# file 'LICENSE.txt', which is part of this source code package.

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
            if item.lifecycle_state != "TERMINATED":
                if item.lifecycle_state != "TERMINATING":
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

# end class GetRouteTable



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
    route_rule,
    route_purge_option):
    
    # get the existing route table
    returned_route_rules = network_client.get_route_table(route_table_id)
    # append to empty list just the route rules from the object only
    # if purge option is not chosen, otherwise proceed to add route
    # and purge all other routes.
    route_rules = []
    if route_purge_option != "--PURGE-THEN-ADD-ROUTE":
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
    network_entity_id,
    destination_route
    ):
    
    # get existing route table and create a list called existing_route_rules
    returned_route_rules = network_client.get_route_table(route_table_id)
    new_route_rules = [] # modified route table will be appended here for entries to retain
    route_rule_found = False # set this to True only if the rule targetting for removal is found

    for item in returned_route_rules.data.route_rules:
        if item.destination != destination_route or \
            item.network_entity_id != network_entity_id:
            new_route_rules.append(item)
        else:
            route_rule_found = True
    # exit out if route rule for removal was not found
    if not route_rule_found:
        return None

    # Now apply new route rule entries to route table after creating route table details
    # that omits the removed route rule
    route_table_details = UpdateRouteTableDetails(
        route_rules = new_route_rules)

    results = network_client.update_route_table(
        rt_id = route_table_id,
        update_route_table_details = route_table_details
    ).data
    if results is not None:
        return results
    else:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR\n")

# end function delete_route_rule()

def update_route_table(network_client,
                    UpdateRouteTableDetails,
                    route_table_id,
                    network_entity,
                    destination_type,
                    destination_route,
                    new_destination_type,
                    new_destination_route,
                    new_route_description
                    ):

                    # get existing route table and create a list called existing_route_rules
                    existing_route_rules = network_client.get_route_table(route_table_id).data.route_rules
                    new_route_rules = [] # modified route table will be appended here for entries to retain
                    route_rule_found = False # set this to True only if the rule targetting for removal is found

                    for item in existing_route_rules:
                        if (item.network_entity_id != network_entity.id and item.destination \
                            != destination_route):
                            new_route_rules.append(item)
                        else:
                            route_rule_found = True
                            item.description = new_route_description
                            item.destination_type = new_destination_type
                            item.destination = new_destination_route
                            new_route_rules.append(item)
                    if not route_rule_found:
                        return None
                    else:
                        # apply the new route rule set after creating the update method
                        route_table_details = UpdateRouteTableDetails(
                            route_rules = new_route_rules)

                        results = network_client.update_route_table(
                            rt_id = route_table_id,
                            update_route_table_details = route_table_details
                        ).data
                        if results is not None:
                            return results
                        else:
                            raise RuntimeError("EXCEPTION! UNKNOWN ERROR\n")
                        
                        
# end function update_route_table()

