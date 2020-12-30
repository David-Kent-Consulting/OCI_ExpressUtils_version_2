#!/usr/bin/python3

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
'''
The system env var PATHONPATH must be exported in the shell's profile. It must point to the location of the OCI
libraries. This is typically in the same directory structure that the OCI CLI installs to, such as
~./lib/oracle-cli/lib/python3.8/site-packages 

Below find a literal example:

export PYTHONPATH=/Users/henrywojteczko/lib/oracle-cli/lib/python3.8/site-packages

See https://docs.python.org/3/tutorial/modules.html#the-module-search-path and
https://stackoverflow.com/questions/54598292/python-modulenotfounderror-when-trying-to-import-module-from-imported-package

Package requirements: Python 3.8.5 or later, conda, pandas.
Be certain your libpaths are correct for python otherwise pandas will not import.

'''
import csv
import os.path
import pandas as pd
import sys
from lib.general import get_protocol
from lib.general import error_trap_resource_not_found
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.securitylists import prepare_csv_record
from lib.securitylists import export_security_list_rules_to_csv
from lib.securitylists import GetNetworkSecurityList
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import EgressSecurityRule
from oci.core.models import IcmpOptions
from oci.core.models import IngressSecurityRule
from oci.core.models import TcpOptions
from oci.core.models import PortRange
from oci.core.models import UdpOptions
from oci.core.models import UpdateSecurityListDetails

if len(sys.argv) != 7:
    print(
        "\n\nOci-ImportSecurityList : Correct Usage\n\n" +
        "Oci-ImportSecurityList.py [parent compartment] [child_compartment] [virtual_network] " +
        "[network security list] [region] [csv file]\n\n" +
        "Use case example imports all security list rules into the specified security list from the CSV input file.\n" +
        "\tOci-ImportSecurityList.py admin_comp auto_comp auto_vcn auto_sec 'us-ashburn-1' auto_sec_rules.csv\n\n" +
        "The format of the CSV is <field1>;<field2>;.......<last field><CR>\n" +
        "The CSV file is named <security list name>_rules.csv and includes a header file that describes each field.\n" +
        "The import program expects this header and ignores it as input.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("exception! - Incorrect Usage\n")


parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
security_list_name              = sys.argv[4]
region                          = sys.argv[5]
security_rule_export_file       = sys.argv[6]

if not os.path.isfile(security_rule_export_file):
    raise RuntimeWarning("WARNING! - File not found")
'''

We define all functions that use pandas within the main program. There are 2 main functions.

Function import_csv_to_dataframe instiates a pandas dataframe that contains the CSV
imported objects.

'''
def import_csv_to_dataframe(
    security_rule_export_file,
    my_delimiter):
    '''
    This function uses pandas to retrieve the data in the CSV rule export file into
    a dataframe. It returns the dataframe to the calling code. For example, if the
    a record contains:
        Rule Description;Protocol (ICMP/ICMPv6/TCP/UDP);Is Stateless (False/True);Source;Source Type;Destination;Destination Type;ICMP Type;ICMP Code;Source TCP Maximum Port;Source TCP Minimum Port;Destination TCP Maximum Port;Destination TCP Minimum Port;Source UDP Maximum Port;Source UDP Minimum Port;Destination UDP Maximum Port;Destination UDP Minimum UDP Port
        Sample rule permits all Inbound TCP traffic from tenancy;TCP;10.1.0.0/20;CIDR_BLOCK;;;;;;;;;;
        Sample rule permits all Inbound TCP traffic from tenancy;TCP;10.1.0.0/20;CIDR_BLOCK;;;;;;;;;;

    And you wish to read the second field in the 1st row, simply doing this will retrieve the data:
    
    my_data = rules.iloc[1,1]
    
    The contents of my_data now are "TCP"
    
    To later extract specific values from the datafrom, use the iloc method.
    See the pandas user guide for more information at
    https://pandas.pydata.org/docs/user_guide/10min.html#object-creation
    '''
    
    # start by opening the CSV import file for reading
    records = pd.read_csv(security_rule_export_file,
                         sep = ";")
    return records

# end function import_csv_to_dataframe()

def import_rules(rules):
    
    count = len(rules)
    cntr = 0 # we skip the header
    ingress_security_rules = []
    egress_security_rules = []

    while cntr < count:
        # we'll test for the protocol type and take action based on the string values "TCP", "UDP", and "ICMP"
        # This release does not support ICMPv6
        if "TCP" == rules.iloc[cntr, 1]:
            
            protocol = "6" # set the RFC protocol acronym to its numeric equivalent, required by the OCI API
            
            # Testing to see if the field for source is empty, we are using pandas
            if str(rules.iloc[cntr,3]) != "nan":
                # now test to see if is_stateless is false, and if so, create a var
                # is_stateless as a boolean False. OCI API requires this.
                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False

                # there is a defect in oci.core.models.TcpOptions when attempting to
                # build it when not called from within oci.core.models.EgressSecurityRule.
                # This big fat bug means we have to do some work-around code to make things work.
                # Must be set to null and then defined only if source and/or destination
                # rules exist. API is loosy goosie, so we must be careful.
                source_max = None
                destination_max = None
                if str(rules.iloc[cntr, 9]) != "nan":
                    source_max = int(rules.iloc[cntr, 9])
                    source_min = int(rules.iloc[cntr, 10])
                if str(rules.iloc[cntr, 11]) != "nan":
                    destination_max = int(rules.iloc[cntr, 11])
                    destination_min = int(rules.iloc[cntr, 12])
                
                # run through the logic, testing for source_max and destination_max. This will determine
                # which OCI APIs get called for the specific rule type to define
                if source_max is not None and destination_max is None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        tcp_options = TcpOptions(
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                elif source_max is None and destination_max is not None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        tcp_options = TcpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            )
                        )
                    )
                elif source_max is not None and destination_max is not None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        tcp_options = TcpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            ),
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                else:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4]
                    )
                ingress_security_rules.append(rule)
            # end if str(rules.iloc[cntr,3]) != "nan":

            # Testing to see if the field for destination is empty
            if str(rules.iloc[cntr,5]) != "nan":
                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False
                
                source_max = None
                destination_max = None
                if str(rules.iloc[cntr, 9]) != "nan":
                    source_max = int(rules.iloc[cntr, 9])
                    source_min = int(rules.iloc[cntr, 10])
                if str(rules.iloc[cntr, 11]) != "nan":
                    destination_max = int(rules.iloc[cntr, 11])
                    destination_min = int(rules.iloc[cntr, 12])
                
                if source_max is not None and destination_max is None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        tcp_options = TcpOptions(
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                elif source_max is None and destination_max is not None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        tcp_options = TcpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            )
                        )
                    )
                elif source_max is not None and destination_max is not None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        tcp_options = TcpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            ),
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                else:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6]
                    )
                egress_security_rules.append(rule)
            # end if str(rules.iloc[cntr,5]) != "nan":
        # end if "TCP" == rules.iloc[cntr, 1]:

        if "UDP" == rules.iloc[cntr, 1]:
            protocol = "17" # set the RFC protocol acronym to its numeric equivalent
            # test for the source
            if str(rules.iloc[cntr,3]) != "nan":
                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False
                
                source_max = None
                destination_max = None
                if str(rules.iloc[cntr, 13]) != "nan":
                    source_max = int(rules.iloc[cntr, 13])
                    source_min = int(rules.iloc[cntr, 14])
                if str(rules.iloc[cntr, 15]) != "nan":
                    destination_max = int(rules.iloc[cntr, 15])
                    destination_min = int(rules.iloc[cntr, 16])

                if source_max is not None and destination_max is None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        udp_options = UdpOptions(
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                elif source_max is not None and destination_max is not None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        udp_options = UdpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            ),
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                elif source_max is None and destination_max is not None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        udp_options = UdpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            )
                        )
                    )
                else:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                    )
                ingress_security_rules.append(rule)
            # end if str(rules.iloc[cntr,3]) != "nan":

            if str(rules.iloc[cntr,5]) != "nan":
                if str(rules.iloc[cntr, 6]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False
                
                source_max = None
                destination_max = None
                if str(rules.iloc[cntr, 13]) != "nan":
                    source_max = int(rules.iloc[cntr, 13])
                    source_min = int(rules.iloc[cntr, 14])
                if str(rules.iloc[cntr, 15]) != "nan":
                    destination_max = int(rules.iloc[cntr, 15])
                    destination_min = int(rules.iloc[cntr, 16])
                
                if source_max is not None and destination_max is None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        udp_options = UdpOptions(
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                elif source_max is not None and destination_max is not None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        udp_options = UdpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            ),
                            source_port_range = PortRange(
                                max = source_max,
                                min = source_min
                            )
                        )
                    )
                elif source_max is None and destination_max is not None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        udp_options = UdpOptions(
                            destination_port_range = PortRange(
                                max = destination_max,
                                min = destination_min
                            )
                        )
                    )
                else:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6]
                    )
                egress_security_rules.append(rule)
            # end if str(rules.iloc[cntr,5]) != "nan":
        # end if "UDP" == rules.iloc[cntr, 1]:

        if "ICMP" == rules.iloc[cntr, 1]:
            protocol = "1" # set the RFC protocol acronym to its numeric equivalent

            if str(rules.iloc[cntr,3]) != "nan":
                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False
                
                # for ICMP, we test for the ICMP type and then the ICMP code. In our
                # code, we presume that where a code exists, a type must also exist.
                # ICMP does not have to have a type/code, or a code, but must have a
                # type if a code is present.
                icmp_type = None
                icmp_code = None
                # test for the type value
                if str(rules.iloc[cntr, 7]) != "nan":
                    icmp_type = int(rules.iloc[cntr, 7])
                # test for the code value
                if str(rules.iloc[cntr, 8]) != "nan":
                    icmp_code = int(rules.iloc[cntr, 8])
                
                # first we test to see if both type and code are present, then create the rule
                if icmp_type is not None and icmp_code is not None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        icmp_options = IcmpOptions(
                            type = icmp_type,
                            code = icmp_code
                        )
                    )
                # Now test to see if only type is present
                elif icmp_type is not None and icmp_code is None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                        icmp_options = IcmpOptions(
                            type = icmp_type
                        )
                    )
                # now we test to see if neither type or code are present
                elif icmp_type is None and icmp_code is None:
                    rule = IngressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        source = rules.iloc[cntr, 3],
                        source_type = rules.iloc[cntr, 4],
                    )
                # finally, we test to see if code is present without type, in which
                # case we raise a RuntimeWarning
                elif icmp_type is None and icmp_code is not None:
                    print(
                        "\n\nWARNING! - ICMP type value is missing for {} but code {} is present\n".format(
                        icmp_code,
                        rules.iloc[cntr, 0]) +
                        "Please resolve and try again.\n\n"
                    )
                    raise RuntimeWarning("WARNING! - ICMP code must always accompany an ICMP type\n")
                ingress_security_rules.append(rule)
            # end if str(rules.iloc[cntr,3]) != "nan":

            if str(rules.iloc[cntr,5]) != "nan":
                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False

                icmp_type = None
                icmp_code = None
                # test for the type value
                if str(rules.iloc[cntr, 7]) != "nan":
                    icmp_type = int(rules.iloc[cntr, 7])
                # test for the code value
                if str(rules.iloc[cntr, 8]) != "nan":
                    icmp_code = int(rules.iloc[cntr, 8])

                if icmp_type is not None and icmp_code is not None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        icmp_options = IcmpOptions(
                            type = icmp_type,
                            code = icmp_code
                        )
                    )
                elif icmp_type is not None and icmp_code is None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6],
                        icmp_options = IcmpOptions(
                            type = icmp_type
                        )
                    )                
                elif icmp_type is None and icmp_code is None:
                    rule = EgressSecurityRule(
                        description = rules.iloc[cntr, 0],
                        is_stateless = is_stateless,
                        protocol = protocol,
                        destination = rules.iloc[cntr, 5],
                        destination_type = rules.iloc[cntr, 6]
                    )    
                elif icmp_type is None and icmp_code is not None:
                    print(
                        "\n\nWARNING! - ICMP type value is missing for {} but code {} is present\n".format(
                        icmp_code,
                        rules.iloc[cntr, 0]) +
                        "Please resolve and try again.\n\n"
                    )
                    raise RuntimeWarning("WARNING! - ICMP code must always accompany an ICMP type\n")
                egress_security_rules.append(rule)
            # end if str(rules.iloc[cntr,5]) != "nan":
        # end     if "ICMP" == rules.iloc[cntr, 1]:

        cntr += 1
    # end while cntr < count
    
    # The object security_list_details is the object that gets passed to network_client.update_security_list
    security_list_details = UpdateSecurityListDetails(
        ingress_security_rules = ingress_security_rules,
        egress_security_rules = egress_security_rules
    )
    
    # now apply the new rule set to the security list
    results = network_client.update_security_list(
        security_list_id = security_list.id,
        update_security_list_details = security_list_details
    ).data

    if results is None:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
    else:
        print(results)

# end function import_rules()

# instiate dict and method objects
config = from_file() # gets ~./.oci/config and reads to the object
config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources

# Get the parent compartment
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
if parent_compartment is None:
    print(
        "\n\nWARNING! - Parent compartment {} not found in tenancy {}.\n".format(
            parent_compartment_name,
            config["tenancy"] +
        "Please try again with a correct compartment name.\n\n"
        )
    )
    raise RuntimeWarning("WARNING! - Compartment not found\n")

# get the child compartment
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
if child_compartment is None:
    print(
        "\n\nWARNING! - Child compartment {} not found in parent compartment {}\n".format(
            child_compartment_name,
            parent_compartment_name
        ) +
        "Please try again with a correct compartment name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Compartment not found\n")

# Get the VCN resource
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
if virtual_cloud_network is None:
    print(
        "\n\nWARNING! - Virtual cloud network {} not found in child compartment {}.\n".format(
            virtual_cloud_network_name,
            child_compartment_name
        ) +
        "Please try again with a correct virtual cloud network name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Virtual cloud network not found\n")

# check to see if the security list exists
security_lists = GetNetworkSecurityList(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    security_list_name
)
security_lists.populate_security_lists()
security_list = security_lists.return_security_list()
error_trap_resource_not_found(
    security_list_name,
    "Security list " + security_list_name + " not found within virtual cloud network " + virtual_cloud_network_name
)

# Start by instiating the rules variable. This will be a pandas dataframe object.
my_rules = import_csv_to_dataframe(
    security_rule_export_file,
    ";")

import_rules(my_rules)
