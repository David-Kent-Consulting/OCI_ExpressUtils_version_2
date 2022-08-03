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
from lib.general import error_trap_resource_found
from tabulate import tabulate
from time import sleep

# required system modules
import os.path
import sys
from time import sleep

# required KENT modules
from lib.general import GetAlarms
from lib.general import copywrite
from lib.general import create_alarm
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
from oci.monitoring.models import CreateAlarmDetails


if len(sys.argv) < 14 or len(sys.argv) > 15:
    print(
        "\n\n\Oci-AddAlarm.py : Usage\n\n" +
        "Oci-AddAlarm.py [parent compartment] [child_compartment] [region] [alarm name] \\\n" +
        "\t[notification item name] [notification item compartment] [namespace] \\\n" +
        "\t[query string] [severity] [repeat notification value] \\\n" +
        "\t[repeat notification units] [alarm message body] [message format] [option --suppress-output]\n\n"
    )
    raise RuntimeWarning ("INVALID USAGE!\n\n")

if len(sys.argv) == 15 and sys.argv[14].upper() == "--SUPPRESS-OUTPUT":
    option = sys.argv[14].upper()
elif len(sys.argv) == 15:
    raise RuntimeWarning("INVALID OPTION\n\n")
else:
    option = None
    copywrite()

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
region                              = sys.argv[3]
alarm_name                          = sys.argv[4]
notification_item_name              = sys.argv[5]
notification_item_compartment_name  = sys.argv[6]
namespace                           = sys.argv[7].lower()
query_string                        = sys.argv[8]
severity                            = sys.argv[9].upper()
repeat_notification_value           = sys.argv[10]
repeat_notification_unit            = sys.argv[11].upper()
message_body                        = sys.argv[12]
message_format                      = sys.argv[13].upper()

# do some input checking
if severity not in ["CRITICAL", "WARNING", "ERROR", "INFO"]:
    raise RuntimeWarning('WARNING! Severity must be a string value of "CRITICAL", "WARNING", "ERROR", "INFO"\n\n')

if repeat_notification_unit not in ["M", "H"]:
    raise RuntimeWarning('WARNING! Repeat notification units must be a string value of "M", "H"\n\n')
else:
    # must be in correct ISO time format, for example, "PT30M" means "present time + 30 minutes"
    repeat_notification_duration = "PT" + repeat_notification_value + repeat_notification_unit

if len(message_body) > 1000:
    raise RuntimeWarning("WARNING! Message body cannot exceed 1000 chars\n\n")

'''
The namespace is the library to which we make queries to OMS. As of 01-feb-2022, there are only 6 name spaces. We
place then in a list and validate that the namespace is of a correct value. Add to this list when new name spaces
are released.
'''
if namespace not in [
    "oci_blockstore",
    "oci_compute",
    "oci_compute_infrastructure_health",
    "oci_computeagent",
    "oci_notification",
    "oci_nat_gateway"
    "oci_vcn"]:
    raise RuntimeWarning("WARNING! Invalid namespace!\n\n")

'''
There are 3 message formats as of 01-feb-2022. Add to the list below if more message formats are added in the
future.
'''
if message_format not in [
    "RAW",
    "PRETTY_JSON",
    "ONS_OPTIMIZED"]:
    raise RuntimeWarning("WARNING! INVALID MESSAGE TYPE\n")

config              = from_file() # gets ~./.oci/config and reads to the object
identity_client     = IdentityClient(config) # builds the identity client method, required to manage compartments
ons_client          = NotificationControlPlaneClient(config)
monitoring_client   = MonitoringClient(config)

# verify the region exists
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
if alarms.populate_alarms(): # see class in lib/general.py
    
    alarm_list = alarms.return_all_alarms()
    alarm = alarms.return_alarm(alarm_name) # get the specific alarm if present

    if alarm is not None: # we do not want to create the alarm if it already exists
        print("\n\nAlarm {} already present in compartment {} within region {}\n".format(
            alarm_name,
            child_compartment_name,
            region
        ))
        raise RuntimeWarning("DUPLICATE ALARMS NOT ALLOWED!\n\n")

    # we must get the compartment ID where the notification item is stored
    notification_item_compartment = None
    for c in child_compartments.return_all_child_compartments():
        if c.name == notification_item_compartment_name:
            notification_item_compartment = c
    error_trap_resource_not_found(
        notification_item_compartment,
        "The notification item compartment " + notification_item_compartment_name + " could not be found in parent compartment " + parent_compartment_name
    )

    # get the notification item
    notification_topics = GetNotificationItems(
        ons_client,
        notification_item_compartment.id)
    if notification_topics.populate_notification_lists(): # see class in lib.general
        notification_item = notification_topics.return_notification_topic(notification_item_name)
    
    # ok, its all good, create the alarm
    create_alarm_response = create_alarm(
        monitoring_client,
        CreateAlarmDetails,
        alarm_name,
        child_compartment.id,
        namespace,
        query_string,
        severity,
        notification_item.topic_id,
        message_body,
        message_format,
        repeat_notification_duration
    )
if option is None: # option is set to None if suppression is not set, so print the output from the alarm creation
    print(create_alarm_response)