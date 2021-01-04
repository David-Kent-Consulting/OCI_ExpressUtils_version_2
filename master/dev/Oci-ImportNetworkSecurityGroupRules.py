#!/Users/henrywojteczko/anaconda3/bin/python

#######################################################
### WARNING! WARNING! WARNING! WARNING! WARNING!    ###
###                                                 ###
### The python interpreter that matches the version ###
### installed with anaconda and pandas must be      ###
### loaded. Failure to do so will result in import  ###
### and runtime erroors.                            ###
###                                                 ###
### WARNING! WARNING! WARNING! WARNING! WARNING!    ###
#######################################################

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

import pandas as pd
import os.path
import sys
from time import sleep
from lib.general import error_trap_resource_not_found
from lib.general import GetInputOptions
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.securitygroups import GetNetworkSecurityGroup
from lib.securitylists import prepare_csv_record
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import VirtualNetworkClient
from oci.core.models import AddSecurityRuleDetails
from oci.core.models import AddNetworkSecurityGroupSecurityRulesDetails
from oci.core.models import PortRange
from oci.core.models import RemoveNetworkSecurityGroupSecurityRulesDetails
from oci.core.models import IcmpOptions
from oci.core.models import TcpOptions
from oci.core.models import UdpOptions

if len(sys.argv) != 7:
    print(
        "\n\nOci-ImportNetworkSecurityGroupRules : Correct Usage\n\n" +
        "Oci-ImportNetworkSecurityGroupRules.py [parent compartment] [child_compartment] [virtual_network] " +
        "[network security group] [region] [csv file]\n\n" +
        "Use case example imports all network security group rules into the specified security group from the CSV input file.\n" +
        "\tOci-ImportNetworkSecurityGroupRules.py admin_comp auto_comp auto_vcn dmzt01_grp 'us-ashburn-1' dmzt01_grp.csv\n\n" +
        "The format of the CSV is <field1>;<field2>;.......<last field><CR>\n" +
        "The CSV file is named <security group name>_rules.csv and includes a header file that describes each field.\n" +
        "The import program expects this header and ignores it as input.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("exception! - Incorrect Usage\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
virtual_cloud_network_name      = sys.argv[3]
security_group_name             = sys.argv[4]
region                          = sys.argv[5]
security_rule_export_file       = sys.argv[6]

if not os.path.isfile(security_rule_export_file):
    raise RuntimeWarning("WARNING! - File not found")

# functions

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

def create_ruleset(
    AddSecurityRuleDetails,
    AddNetworkSecurityGroupSecurityRulesDetails,
    IcmpOptions,
    TcpOptions,
    UdpOptions,
    PortRange,
    network_client,
    network_security_group_id,
    rules):
    '''

    The purpose of this function is to import network security group rules created within a correctly
    formatted csv file into the security list. The OCI APIs for managing security groups are complex
    and have some stability issues. For example, calling APIs for building security rules as stand-alone
    code yields undefined type casting of classes and decorators. The sole means of avoiding these
    defects is to call the APIs recursively within the code block that calls oci.core.VirtualNetworkClient

    This function presumes the security group rules are purged prior to being called. A failure to purge
    the rules will result in duplicates. Duplicates are not enforced by OCI.

    '''
    
    count = len(rules)
    cntr = 0 # we skip the header since pandas is used
    rule_set = []   # Unlike security lists, security rules do not require calls for either
                    # engress or ingress rules. So we only define one list and append as each
                    # rule is defined, regardless of type.
    while cntr < count:
        # we'll test for the protocol type and take action based on the string values "TCP", "UDP", and "ICMP"
        # This release does not support ICMPv6
        if "TCP" == rules.iloc[cntr, 1]:
            
            protocol = "6" # set the RFC protocol acronym to its numeric equivalent, required by the OCI API

            # is_stateless as a boolean False. OCI API requires this.
            if str(rules.iloc[cntr, 2]) == "True":
                is_stateless = True
            else:
                is_stateless = False

            # There is a defect in oci.core.VirtualNetworkClient.list_network_secuirty_group_rules
            # The API returns null instead of a boolean value. Since stateless is a rarely used
            # rule type, we presume a string value of "True" will specify stateless, otherwise
            # we set to False. In either case, we are setting to boolean per API requirements.
            # This defect was reported on 31-dec-2021 via SR 3-24851209151.
            source_max = None
            destination_max = None
            if str(rules.iloc[cntr, 9]) != "nan":
                source_max = int(rules.iloc[cntr, 9])
                source_min = int(rules.iloc[cntr, 10])
            if str(rules.iloc[cntr, 11]) != "nan":
                destination_max = int(rules.iloc[cntr, 11])
                destination_min = int(rules.iloc[cntr, 12])

            # Testing to see if the field for source is empty, we are using pandas
            if str(rules.iloc[cntr,3]) != "nan":

                '''

                In all code below, we must apply each rule individually. This is due to the
                API stability issues previously discussed at the top of this function. In each case,
                we determine how to build the protocol options object based on the presence of vars
                instiated and then set with values when said values are present. This strategy is
                repeated throughout the function.

                '''
                if source_max is not None and destination_max is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    tcp_options = TcpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    tcp_options = TcpOptions(
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is not None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    tcp_options = TcpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        ),
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                else:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4]
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
            # Test for the destination
            if str(rules.iloc[cntr, 5]) != "nan":

                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False

                if source_max is not None and destination_max is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    tcp_options = TcpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    tcp_options = TcpOptions(
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is not None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    tcp_options = TcpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        ),
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                else:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6]
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
        # end if "TCP" == rules.iloc[cntr, 1]:
        if "UDP" == rules.iloc[cntr, 1]:
            
            protocol = "17"

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
            
            # test for the source
            if str(rules.iloc[cntr,3]) != "nan":
                
                if source_max is not None and destination_max is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    udp_options = UdpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    udp_options = UdpOptions(
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is not None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    udp_options = UdpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        ),
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                else:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4]
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
            # test for the destination    
            if str(rules.iloc[cntr, 5]) != "nan":
                
                if source_max is not None and destination_max is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    udp_options = UdpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    udp_options = UdpOptions(
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif source_max is not None and destination_max is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    udp_options = UdpOptions(
                                        source_port_range = PortRange(
                                            max = source_max,
                                            min = source_min
                                        ),
                                        destination_port_range = PortRange(
                                            max = destination_max,
                                            min = destination_min
                                        )
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                else:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6]
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)

        # end if "UDP" == rules.iloc[cntr, 1]:
        
        if "ICMP" == rules.iloc[cntr, 1]:
            
            protocol = "1"

            icmp_type = None
            icmp_code = None
            if str(rules.iloc[cntr, 7]) != "nan":
                icmp_type = int(rules.iloc[cntr, 7])
            if str(rules.iloc[cntr, 8]) != "nan":
                icmp_code = int(rules.iloc[cntr, 8])
                
            if str(rules.iloc[cntr, 2]) == "True":
                is_stateless = True
            else:
                is_stateless = False
            
            if str(rules.iloc[cntr,3]) != "nan":
                
                if icmp_type is not None and icmp_code is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    icmp_options = IcmpOptions(
                                        type = icmp_type
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif icmp_type is not None and icmp_code is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4],
                                    icmp_options = IcmpOptions(
                                        type = icmp_type,
                                        code = icmp_code
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif icmp_type is None and icmp_code is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "INGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    source = rules.iloc[cntr, 3],
                                    source_type = rules.iloc[cntr, 4]
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)

            if str(rules.iloc[cntr,5]) != "nan":

                if icmp_type is not None and icmp_code is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    icmp_options = IcmpOptions(
                                        type = icmp_type
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif icmp_type is not None and icmp_code is not None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6],
                                    icmp_options = IcmpOptions(
                                        type = icmp_type,
                                        code = icmp_code
                                    )
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
                elif icmp_type is None and icmp_code is None:
                    results = network_client.add_network_security_group_security_rules(
                        network_security_group_id = network_security_group_id,
                        add_network_security_group_security_rules_details = \
                        AddNetworkSecurityGroupSecurityRulesDetails(
                            security_rules = [
                                AddSecurityRuleDetails(
                                    direction = "EGRESS",
                                    protocol = protocol,
                                    description = rules.iloc[cntr, 0],
                                    destination = rules.iloc[cntr, 5],
                                    destination_type = rules.iloc[cntr, 6]
                                )
                            ]
                        )
                    ).data
                    rule_set.append(results)
                    sleep(1)
        # end if "ICMP" == rules.iloc[cntr, 1]:

        if "ALL" == rules.iloc[cntr, 1]:

            protocol = "all"

            if str(rules.iloc[cntr, 2]) == "True":
                is_stateless = True
            else:
                is_stateless = False
            
            if str(rules.iloc[cntr,3]) != "nan":

                results = network_client.add_network_security_group_security_rules(
                    network_security_group_id = network_security_group_id,
                    add_network_security_group_security_rules_details = \
                    AddNetworkSecurityGroupSecurityRulesDetails(
                        security_rules = [
                            AddSecurityRuleDetails(
                                direction = "INGRESS",
                                protocol = protocol,
                                description = rules.iloc[cntr, 0],
                                source = rules.iloc[cntr, 3],
                                source_type = rules.iloc[cntr, 4]
                            )
                        ]
                    )
                ).data
                rule_set.append(results)
                sleep(1)
        
            if str(rules.iloc[cntr,5]) != "nan":

                if str(rules.iloc[cntr, 2]) == "True":
                    is_stateless = True
                else:
                    is_stateless = False

                results = network_client.add_network_security_group_security_rules(
                    network_security_group_id = network_security_group_id,
                    add_network_security_group_security_rules_details = \
                    AddNetworkSecurityGroupSecurityRulesDetails(
                        security_rules = [
                            AddSecurityRuleDetails(
                                direction = "EGRESS",
                                protocol = protocol,
                                description = rules.iloc[cntr, 0],
                                destination = rules.iloc[cntr, 5],
                                destination_type = rules.iloc[cntr, 6]
                            )
                        ]
                    )
                ).data
                rule_set.append(results)
                sleep(1)

        cntr += 1
        # end while cntr < count

    # now return the rulesets that were created
    return rule_set
# end function create_ruleset()

def purge_rules_from_network_security_group(
    network_client,
    my_security_group):

    ruleset = security_groups.return_security_group_rules(my_security_group.id)
    # build a list of security rule IDs, which is required by the API
    security_rule_ids = []
    for rule in ruleset:
        security_rule_ids.append(rule.id)
    # call remove_network_security_group_security_rules and remove the rules supplied
    # in the list. API returns result regardless of presence of rules, which is desirable
    # logic. We must sleep for 1 cycle in order to avoid API stability issues.
    results = network_client.remove_network_security_group_security_rules(
        security_group.id,
        remove_network_security_group_security_rules_details = RemoveNetworkSecurityGroupSecurityRulesDetails(
            security_rule_ids = security_rule_ids
        )
    )
    sleep(1)

# end function purge_rules_from_network_security_group()

# instiate the environment
config = from_file() # gets ~./.oci/config and reads to the object
config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
network_client = VirtualNetworkClient(config) # builds the network client method, required to manage network resources

# get the parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Child compartment " + child_compartment_name + " within parent compartment " + parent_compartment_name
)


# Get the VCN resource
virtual_cloud_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_cloud_network_name)
virtual_cloud_networks.populate_virtual_cloud_networks()
virtual_cloud_network = virtual_cloud_networks.return_virtual_cloud_network()
error_trap_resource_not_found(
    virtual_cloud_network,
    "Virtual cloud network " + virtual_cloud_network_name + " not found within child compartment " + child_compartment_name
)

security_groups = GetNetworkSecurityGroup(
    network_client,
    child_compartment.id,
    virtual_cloud_network.id,
    security_group_name
)
security_groups.populate_security_groups()
security_group = security_groups.return_security_group()
error_trap_resource_not_found(
    security_group,
    "Security group " + security_group_name + " not found within virtual cloud network " + virtual_cloud_network_name
)

# We start by importing the correctly formatted CSV file.
my_rules = import_csv_to_dataframe(
    security_rule_export_file,
    ";")
print("\n\n{} records imported from CSV file {}\n".format(
    len(my_rules),
    security_rule_export_file))

# We continue by purging any existing rules from the security group. This is to enforce avoidence of duplicate records
print("Purging existing security rules from network security group {}\n".format(security_group_name))
purge_rules_from_network_security_group(
    network_client,
    security_group
)

# Proceed with the record import.
print("Importing rules from CSV file {} into network security list {}\n".format(
    security_rule_export_file,
    security_group_name
))
ruleset = create_ruleset(
    AddSecurityRuleDetails,
    AddNetworkSecurityGroupSecurityRulesDetails,
    IcmpOptions,
    TcpOptions,
    UdpOptions,
    PortRange,
    network_client,
    security_group.id,
    my_rules)
print("Import of new security rules successful. Printing rules below and exiting normally.\n\n")
sleep(3)
print(ruleset)
