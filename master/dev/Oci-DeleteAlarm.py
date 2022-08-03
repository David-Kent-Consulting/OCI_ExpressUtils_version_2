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
from lib.general import warning_beep
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

copywrite()

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-DeleteAlarm.py : Usage\n\n" +
        "Oci-DeleteAlarm.py [parent_compartment] [child_compartment] [alarm_name] [region] [--force option]\n\n" +
        "Use case example below deletes the specified alarm within the specified compartment\n" +
        "\tOci-DeleteAlarm.py admin_comp auto_comp vcn_alarm_type_VnicConntrackIsFull 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! INVALID USAGE\n")

if len(sys.argv) == 6 and sys.argv[5].upper() == "--FORCE":
    option = sys.argv[5].upper()
elif len(sys.argv) == 5:
    option = None
else:
    raise RuntimeWarning("WARNING! INVALID OPTION\n")

parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
alarm_name                          = sys.argv[3]
region                              = sys.argv[4]

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
    error_trap_resource_not_found(
        alarm,
        "Alarm " + alarm_name + " not found in compartment " + child_compartment_name + " within region " + region
    )

    if option is None:
        warning_beep(1)
        print("Enter YES to delete alarm {} from compartment {} within region {} or press enter to abort......".format(
            alarm_name,
            child_compartment_name,
            region
        ))
        if "YES" != input():
            print("Alarm deletion aborted per user request.\n\n")
            exit(0)

    delete_alarm_response = monitoring_client.delete_alarm(
        alarm_id = alarm.id
    )

    print("Alarm {} deleted from compartment {} within region {}\n".format(
        alarm_name,
        child_compartment_name,
        region
    ))
    print(delete_alarm_response.headers)

else:
    raise RuntimeError("UNKNOWN ERROR\n")