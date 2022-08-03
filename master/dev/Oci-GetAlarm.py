#!/usr/bin/python3

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
'''
The system env var PATHONPATH must be exported in the shell's profile. It must point to the location of the OCI
libraries. This is typically in the same directory structure that the OCI CLI installs to, such as
~./lib/oracle-cli/lib/python3.8/site-packages 

Below find a literal example:

export PYTHONPATH=/Users/henrywojteczko/lib/oracle-cli/lib/python3.8/site-packages

See https://docs.python.org/3/tutorial/modules.html#the-module-search-path and
https://stackoverflow.com/questions/54598292/python-modulenotfounderror-when-trying-to-import-module-from-imported-package

'''
# required system modules
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required system modules
import os.path
import sys
from time import sleep

# required KENT modules
from lib.general import GetAlarms
from lib.general import copywrite
from lib.general import get_regions
from lib.general import error_trap_resource_not_found
from lib.general import GetNotificationItems
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.monitoring import MonitoringClient
from oci.ons import NotificationControlPlaneClient

copywrite()

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetAlarms.py : Usage\n\n" +
        "Oci-GetAlarms.py [parent compartment] [child_compartment] [alarm name] [region] [option]\n\n" +
        "Use case below lists all alarms within the specified compartment:\n" +
        "\tOci-GetAlarms.py admin_comp auto_comp list_all_alarms 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Invalid Usage\n\n")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
alarm_name                              = sys.argv[3]
region                                  = sys.argv[4]

if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None
if option not in ["--JSON", None]:
    print("\n\nINVALID OPTION! Valid options include:\n" +
    "\t--json - list all output in JSON format"
    )
    raise RuntimeWarning("INVLID OPTION!\n")

# instiate required OCI methods

config              = from_file() # gets ~./.oci/config and reads to the object
identity_client     = IdentityClient(config) # builds the identity client method, required to manage compartments
ons_client          = NotificationControlPlaneClient(config)
monitoring_client   = MonitoringClient(config)

regions = get_regions(identity_client)
correct_region = False
for rg in regions:
    if rg.name == region:
        correct_region = True
if not correct_region:
    print("\n\nWARNING! - Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

# get the parent compartment data
parent_compartments                 = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment                  = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment data
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


alarms = GetAlarms(monitoring_client, child_compartment.id)
if alarms.populate_alarms():
    
    alarm_list = alarms.return_all_alarms()
    alarm = alarms.return_alarm(alarm_name)
    error_trap_resource_not_found(
        alarm_list,
        "No alarms found in compartment " + child_compartment_name + " within region " + region
    )


    if alarm_name.upper() == "LIST_ALL_ALARMS":

        if option == "--JSON":
            print(alarm_list)

        else:

            header = [
                "COMPARTMENT",
                "ALARM",
                "NOTIFICATION\nITEM\nNAME",
                "NOTIFICATION\nITEM\nCOMPARTMENT\nNAME"
                "IS ENABLED",
                "OMS\nNAMESPACE",
                "OMS QUERY",
                "SEVERITY",
                "SUPPRESSION",
                "REGION"
            ]
            data_rows = []
            for a in alarm_list:
                '''
                We need to get the notification object first, so we can pull the name. We only grab the first
                ID since our tools only support 1 notification ID per alarm. Then we must set vars that get
                added to data_row based on logic that determines if the alarm is enabled and if alarm
                suppression is enabled. We also pull the child compartment name where the notification item is.
                '''
                # get the first destination notification item
                get_topic_response = ons_client.get_topic(
                    a.destinations[0]
                ).data

                # set the value for notification name, alarm_enabled, and supression_enabled
                if a.is_enabled:
                    alarm_enabled = "TRUE"
                else:
                    alarm_enabled = "FALSE"
                if a.suppression is None:
                    alarm_suppression = "FALSE"
                else:
                    alarm_suppression = "TRUE"
                if get_topic_response.name is not None:
                    notification_topic_name = get_topic_response.name
                                    # get the notification's compartment name
                    notification_topic_compartment_response = identity_client.get_compartment(
                        compartment_id = get_topic_response.compartment_id
                    ).data
                else:
                    notification_topic_name = None
                    notification_topic_compartment_response = None

                # set the values for data_row and then append to data_rows
                data_row = [
                    child_compartment_name,
                    a.display_name,
                    notification_topic_name,
                    notification_topic_compartment_response.name,
                    alarm_enabled,
                    a.namespace,
                    a.query,
                    a.severity,
                    alarm_suppression,
                    region
                ]
                data_rows.append(data_row)

            print(tabulate(data_rows, headers = header, tablefmt = "grid"))

    else:
        if option == "--JSON":
            print(alarm)
        else:

            '''
            Do the same as the above except only on the record we are working against if found
            '''

            error_trap_resource_not_found(
                alarm,
                "Alarm " + alarm_name + " not found in compartment " + child_compartment_name + " within region " + region
            )

            if alarm.is_enabled:
                alarm_enabled = "TRUE"
            else:
                alarm_enabled = "FALSE"
            if alarm.suppression is None:
                alarm_suppression = "FALSE"
            else:
                alarm_suppression = "TRUE"

            get_topic_response = ons_client.get_topic(
                alarm.destinations[0]
            ).data
            if get_topic_response.name is not None:

                notification_topic_name = get_topic_response.name
                notification_topic_compartment_response = identity_client.get_compartment(
                    compartment_id = get_topic_response.compartment_id
                ).data

            else:
                notification_topic_name = None
                notification_topic_compartment_response = None




            header = [
                "COMPARTMENT",
                "ALARM",
                "NOTIFICATION\nITEM\nNAME",
                "NOTIFICATION\nITEM\nCOMPARTMENT\nNAME"
                "IS ENABLED",
                "OMS\nNAMESPACE",
                "OMS QUERY",
                "SEVERITY",
                "SUPPRESSION",
                "REGION"
            ]

            data_rows = [[
                child_compartment_name,
                alarm.display_name,
                get_topic_response.name,
                notification_topic_compartment_response.name,
                alarm_enabled,
                notification_topic_name,
                alarm.namespace,
                alarm.query,
                alarm_suppression,
                region
            ]]

            print(tabulate(data_rows, headers = header, tablefmt = "simple"))

else:
    
    raise RuntimeWarning("WARNING! - class data already populated with data")