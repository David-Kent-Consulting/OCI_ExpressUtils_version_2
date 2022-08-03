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
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.monitoring import MonitoringClient
from oci.ons import NotificationControlPlaneClient

copywrite()

if len(sys.argv) < 4 or len(sys.argv) > 5:
    print(
        "\n\nOci-PurgeAlarmsInCompartment.py : Usage\n\n" +
        "Oci-PurgeAlarmsInCompartment.py [parent compartment] [child_compartment] [region] [--force option]\n\n" +
        "Use case below deletes all alarms within the specified compartment:\n" +
        "\tOci-PurgeAlarmsInCompartment.py admin_comp auto_comp 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Invalid Usage\n\n")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
region                                  = sys.argv[3]

if len(sys.argv) == 5 and sys.argv[4].upper() != "--FORCE":
    raise RuntimeWarning("WARNING! INVALID OPTION\n")
elif len(sys.argv) == 4:
    option = None
else:
    option = sys.argv[4].upper()

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

    error_trap_resource_not_found(
        alarm_list,
        "No alarms found in compartment " + child_compartment_name + " within region " + region
    )

if option != "--FORCE":
    warning_beep(1)
    print(
        "This utility will delete all alarms in compartment {} within region {}\n".format(
            child_compartment_name,
            region
    ))
    print("Enter YES to proceed or press enter to abort.")
    if "YES" != input():
        print("Alarm purge aborted by user.\n\n")
        exit(0)

# start deleting the alarms

for a in alarm_list:

    print("\n\nDeleting alarm {}......\n".format(a.display_name))
    delete_alarm_response = monitoring_client.delete_alarm(
        alarm_id = a.id
    )
    print(delete_alarm_response.headers)
    sleep(1)

print("\n\nAll alarms have been purged from compartment {} within region {}\n".format(
    child_compartment_name,
    region
))

