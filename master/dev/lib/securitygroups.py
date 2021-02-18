import csv
import os
from lib.general import get_protocol
from oci.core import VirtualNetworkClient

class GetNetworkSecurityGroup:
    
    def __init__(
        self,
        network_client,
        compartment_id,
        vcn_id,
        security_group_name):
        
        self.network_client = network_client
        self.compartment_id = compartment_id
        self.vcn_id = vcn_id
        self.security_group_name = security_group_name
        self.security_groups = []
        self.security_group_rules = []
        
    def populate_security_groups(self):
        if len(self.security_groups) != 0:
            return None
        else:
            results = self.network_client.list_network_security_groups(
                compartment_id = self.compartment_id,
                vcn_id = self.vcn_id).data
            
            for item in results:
                if item.lifecycle_state != "TERMINATED":
                    if item.lifecycle_state != "TERMINATING":
                        self.security_groups.append(item)
    
    def return_security_group_rules(self, security_group_id):
        if len(self.security_groups) == 0:
            return None
        else:
            results = self.network_client.list_network_security_group_security_rules(
                network_security_group_id = security_group_id
            ).data

            if results is None:
                return None
            else:
                return(results)


                    

    def return_all_security_groups(self):
        if len(self.security_groups) == 0:
            return None
        else:
            return self.security_groups
        
    def return_security_group(self):
        if len(self.security_groups) == 0:
            return None
        else:
            for item in self.security_groups:
                if item.display_name == self.security_group_name:
                    return item
    
    def __str__(self):
        return "Method setup to perform tasks on " + self.security_group_name

# end class GetNetworkSecurityGroup

def add_security_group(
    network_client,
    CreateNetworkSecurityGroupDetails,
    compartment_id,
    vcn_id,
    security_group_name):
    
    security_group_details = CreateNetworkSecurityGroupDetails(
        compartment_id = compartment_id,
        display_name = security_group_name,
        vcn_id = vcn_id)
    
    results = network_client.create_network_security_group(
        create_network_security_group_details = security_group_details).data
    
    return results

# end function GetNetworkSecurityGroup()

def delete_security_group(
    network_client,
    network_security_group_id):
    
    results = network_client.delete_network_security_group(
        network_security_group_id = network_security_group_id)
    
    return results

# end function delete_security_group()

def add_vnic_to_security_group(
    network_client,
    UpdateVnicDetails,
    vnic_id,
    nsg_id):
    '''
    This function adds a vnic to a network security group. Your code must handle
    all pre-reqs and error conditions. Our code only supports 1 network security
    group per vnic. OCI will support many security groups per vnic. We consider
    this overly complex, and thus enforce 1 security group per vnic.
    '''
    update_vnic_response = network_client.update_vnic(
        vnic_id = vnic_id,
        update_vnic_details = UpdateVnicDetails(
            nsg_ids = [nsg_id]
        )
    ).data
    
    return update_vnic_response

# end function add_vnic_to_security_group()

def delete_vnic_from_network_security_group(
    network_client,
    UpdateVnicDetails,
    vnic_id):
    '''
    This function removes a VNIC from all security groups. Your code must handle
    all pre-reqs and error conditions. Our code only supports 1 network security
    group per vnic. OCI will support many security groups per vnic. We consider
    this overly complex, and thus enforce 1 security group per vnic. So when we
    drop a vnic from a security group, we drop it from all security groups.
    '''
    
    update_vnic_response = network_client.update_vnic(
        vnic_id = vnic_id,
        update_vnic_details = UpdateVnicDetails(
            nsg_ids = []
        )
    ).data
    
    return update_vnic_response

# end function delete_vnic_from_network_security_group()


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

def export_security_group_rules(
    my_export_file,
    my_security_group_rules,
    my_delimiter):

    with open(my_export_file, 'w', newline = "") as csvfile:
        egresswriter = csv.writer(
            csvfile,
            delimiter = my_delimiter
        )

        # create the CSV header
        egresswriter.writerow([
            "Rule Description",
            "Protocol (ICMP/ICMPv6/TCP/UDP)",
            "Is Stateless",
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

        '''
        
        We choose to re-write the functions prepare_csv_record instead of 
        importing from lib.securitylists.py since there are slight differences
        between the APIs for managing network security groups.

        There is an API defect. The method is_stateless returns a null value rather
        than a boolean value. SR 3-24851209151 was opened on 31-dec-2020 regarding
        this defect. All use of this API function will account for the defect by ignoring
        the is_stateless field. See Oci-ImportNetworkSecurityGroupRules.py and look for
        fucntion import_rules to see the work-around. This code should note require
        modification once the defect is resolved.

        '''
        for rule in my_security_group_rules:
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

# end function export_security_group_rules()