# Copyright 2019 – 2020 David Kent Consulting, Inc.
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

import csv
import os
from oci.core import VirtualNetworkClient
from lib.general import get_protocol

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
                if item.lifecycle_state != "TERMINATED":
                    if item.lifecycle_state != "TERMINATING":
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

def prepare_csv_record(my_rule):
    
    csv_record = {
        "description"  : "",
        "icmp_options" : {
            "code" : "",
            "type" : ""
        }, # end icmp_options
        "is_stateless" : "",
        "protocol" : "",
        "destination" : "",
        "destination_type" : "",
        "source" : None,
        "source_type" : "",
        "tcp_options" : {
            "destination_port_range" : {
                "max" : "",
                "min" : ""
            },
            "source_port_range" : {
                "max" : "",
                "min" : ""
            }
        }, # end tcp_options
        "udp_options": {
            "destination_port_range" : {
                "max" : "",
                "min" : ""
            },
            "source_port_range" : {
                "max" : "",
                "min" : ""
            }
        } # end udp_options
    } # end of dictionary object csv_record
    
    # Set the protocol to the textual acronym type per the RFCs
    protocol = get_protocol(my_rule.protocol)
    
    # populate the dictionary object with all common data
    csv_record["description"]   = my_rule.description
    csv_record["is_stateless"]  = my_rule.is_stateless
    csv_record["protocol"]      = protocol
    
    # set the source value data if record type is a source rule
    # my_rule is a class of type oci.core.models.egress_security_rule.EgressSecurityRule
    # therefore we must first test to see if the attribute "source" exists using getattr
    # 3 args, the first being the object, the second being the attribute we are searching
    # for, and the 3rd telling getattr to return None if the attribute is not found.
    # We use this logic throughout the code so as to have 1 function that builds the CSV
    # record.
    if getattr(my_rule, "source", None) is not None:
        csv_record["source"]      = my_rule.source
        csv_record["source_type"] = my_rule.source_type
    
    # now do the same for destination type
    if getattr(my_rule, "destination", None) is not None:
        csv_record["destination"]      = my_rule.destination
        csv_record["destination_type"] = my_rule.destination_type
        
    # run through the logic based on the type of protocol
    if protocol == "ICMP":
        if getattr(my_rule, "icmp_options", None) is not None:
            csv_record["icmp_options"]["code"] = my_rule.icmp_options.code
            csv_record["icmp_options"]["type"] = my_rule.icmp_options.type
    elif protocol == "TCP":
        if getattr(my_rule, "tcp_options", None) is not None:
            # get data for destination ports if present
            if getattr(my_rule.tcp_options, "destination_port_range", None) is not None:
                csv_record["tcp_options"]["destination_port_range"]["max"] = \
                    my_rule.tcp_options.destination_port_range.max
                csv_record["tcp_options"]["destination_port_range"]["min"] = \
                    my_rule.tcp_options.destination_port_range.min
            # get data for source ports if present
            if getattr(my_rule.tcp_options, "source_port_range", None) is not None:
                csv_record["tcp_options"]["source_port_range"]["max"] = \
                    my_rule.tcp_options.source_port_range.max
                csv_record["tcp_options"]["source_port_range"]["min"] = \
                    my_rule.tcp_options.source_port_range.min
    elif protocol == "UDP":
        if getattr(my_rule, "udp_options", None) is not None:
            # get data for destination ports if present
            if getattr(my_rule.udp_options, "destination_port_range", None) is not None:
                csv_record["udp_options"]["destination_port_range"]["max"] = \
                    my_rule.udp_options.destination_port_range.max
                csv_record["udp_options"]["destination_port_range"]["min"] = \
                    my_rule.udp_options.destination_port_range.min
            # get data for source ports if present
            if getattr(my_rule.udp_options, "source_port_range", None) is not None:
                csv_record["udp_options"]["source_port_range"]["max"] = \
                    my_rule.udp_options.source_port_range.max
                csv_record["udp_options"]["source_port_range"]["min"] = \
                    my_rule.udp_options.source_port_range.min
    return csv_record

# end function prepare_csv_record()

def export_security_list_rules_to_csv(
    my_export_file,
    combined_security_list,
    my_delimiter):
    
    with open(my_export_file, 'w', newline = "") as csvfile:
        egresswriter = csv.writer(
            csvfile,
            delimiter = my_delimiter)
        
        # create the CSV header
        egresswriter.writerow([
            "Rule Description",
            "Protocol (ICMP/ICMPv6/TCP/UDP)",
            "Is Stateless (False/True)",
            "Source",
            "Source Type",
            "Destination",
            "Destination Type",
            "ICMP Type",
            "ICMP Code",
            "Source TCP Maximum Port",
            "Source TCP Minimum Port",
            "Destination TCP Maximum Port",
            "Destination TCP Minimum Port",
            "Source UDP Maximum Port",
            "Source UDP Minimum Port",
            "Destination UDP Maximum Port",
            "Destination UDP Minimum UDP Port"
        ])
        
        # write out the rules in CSV format
        for rule in combined_security_list:
            csv_record = prepare_csv_record(rule)
            egresswriter.writerow([
                csv_record["description"],
                csv_record["protocol"],
                csv_record["is_stateless"],
                csv_record["source"],
                csv_record["source_type"],
                csv_record["destination"],
                csv_record["destination_type"],
                csv_record["icmp_options"]["type"],
                csv_record["icmp_options"]["code"],
                csv_record["tcp_options"]["source_port_range"]["max"],
                csv_record["tcp_options"]["source_port_range"]["min"],
                csv_record["tcp_options"]["destination_port_range"]["max"],
                csv_record["tcp_options"]["destination_port_range"]["min"],
                csv_record["udp_options"]["source_port_range"]["max"],
                csv_record["udp_options"]["source_port_range"]["min"],
                csv_record["udp_options"]["destination_port_range"]["max"],
                csv_record["udp_options"]["destination_port_range"]["min"]
            ])

# end function export_security_list_rules_to_csv()