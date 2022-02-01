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

'''
# required system modules
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required KENT modules
from lib.general import copywrite
from lib.general import get_regions
from lib.general import error_trap_resource_not_found
from lib.general import GetNotificationItems
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.ons import NotificationControlPlaneClient

copywrite()

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetNotifications.py : Usage\n\n" +
        "Oci-GetNotifications.py [parent compartment] [child_compartment] [notifcation list name] [region] [option]\n\n" +
        "Use case below lists all notification items within the specified compartment:\n" +
        "\tOci-GetNotifications.py admin_comp auto_comp list_all_notification_items 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Invalid Usage\n\n")

parent_compartment_name                 = sys.argv[1]
child_compartment_name                  = sys.argv[2]
notification_item_name                  = sys.argv[3]
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
ons_client          = NotificationControlPlaneClient(config) # method for managing the notification backplane


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

# get the notifiations items in the compartment and process based on inputs

notification_topics = GetNotificationItems(
    ons_client,
    child_compartment.id)
    
if notification_topics.populate_notification_lists():

    notification_list = notification_topics.return_all_notificaton_topics()                     # populate the class
    notification_item = notification_topics.return_notification_topic(notification_item_name)   # extract the item or get None if not present

    header = [
    "PARENT\n\COMPARTMENT",
    "CHILD\nCOMPARTMENT",
    "NOTIFICATION\nITEM\nNAME",
    "LIFECYCLE\nSTATE",
    "REGION",
    "OCID"
]
    
    if notification_item_name.upper() == "LIST_ALL_NOTIFICATION_ITEMS":

        error_trap_resource_not_found(
            notification_list,
            "No notification items found in compartment " + child_compartment_name + " within region " + region
        )

        if option == "--JSON" and len(notification_list) is not None:

            print(notification_list)
        else:

            data_rows = []
            for n in notification_list:
                data_row = [
                    parent_compartment_name,
                    child_compartment_name,
                    n.name,
                    n.lifecycle_state,
                    region
                ]
                data_rows.append(data_row)
            print(tabulate(data_rows, headers = header, tablefmt = "grid"))

    else:

        error_trap_resource_not_found(
            notification_item,
            "Notification item " + notification_item_name + " not found in compartment " + child_compartment_name + " within region " + region
        )

        if option == None:

            data_rows = [[
                parent_compartment_name,
                child_compartment_name,
                notification_item.name,
                notification_item.lifecycle_state,
                region,
                notification_item.topic_id
            ]]
            print(tabulate(data_rows, headers = header, tablefmt = "simple"))

        elif option == "--JSON":
            print(notification_item)

else:
    raise RuntimeError("ERROR! - GetNotificationItems is already populated with data")