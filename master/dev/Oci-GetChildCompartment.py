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
from datetime import date

# required DKC modules
from lib.general import copywrite
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments

# required OCI modules
import oci
import lib.compartments


option = [] # must have a len() == 0 for subsequent logic to work


# end check_for_duplicates
# We require the parent compartment name for this tool. An option can be passed as the second
# argument.
if len(sys.argv) < 3 or len(sys.argv) > 4: # ARGS PLUS COMMAND
    print(
        "Oci-GetChildCompartment.py : Correct Usage\n\n" +
        "Oci-GetChildCompartment.py [parent compartment name] [child compartment] [optional argument]\n\n" +
        "Use case example 1 prints just the child compartment object that is subordinate\n" +
        "to the supplied parent compartment.\n\n" +
        "Oci-GetChildCompartment.py admin_comp auto_comp\n\n" +
        "Use case example 2 prints all child compartments that are subordinate to the\n" +
        "supplied parent compartment\n\n" +
        "Oci-GetChildCompartment.py admin_comp list_all_child_compartments\n\n" +
        "Use case example 3 prints the child compartment's OCID\n"
        "Oci-GetChildCompartment.py admin_comp auto_comp --ocid\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n"
        )

    raise RuntimeError(
        "EXCEPTION! Incorrect usage."
    )
if len(sys.argv) == 4:
    option = sys.argv[3].upper()
if option != "--JSON":
    copywrite()
    sleep(2)

parent_compartment_name = sys.argv[1]
child_compartment_name = sys.argv[2]

# initialize the environment

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
# this instiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# We create the method my_compartments from the DKC API 
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()

parent_compartment = parent_compartments.return_parent_compartment()

if parent_compartment is None:
    print("\n\nParent compartment name {} not found in tenancy {}\n\n".format(
        parent_compartment_name, config["tenancy"] + "\n" +
        "Please try again with a correct name.\n"
        )
    )
    raise RuntimeWarning("WARNING! - Parent compartment not found")

# # populate child compartments
child_compartments = GetChildCompartments(
    parent_compartments.return_parent_compartment().id,
    child_compartment_name,
    identity_client
    )
child_compartments.populate_compartments()

if child_compartment_name.upper() == "LIST_ALL_CHILD_COMPARTMENTS":
    # print(child_compartments.return_all_child_compartments())
    header = ["COMPARTMENT NAME", "DATE CREATED", "OCID"]
    data_rows = []
    if child_compartments.return_all_child_compartments() is not None:
        for compartment in child_compartments.return_all_child_compartments():
            data_row = [
                compartment.name,
                date.strftime(compartment.time_created, '%Y-%m-%d %H:%M:%S'),
                compartment.id
            ]
            data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:
    child_compartment = child_compartments.return_child_compartment()
    if child_compartment is None:
        print("\nChild compartment {} not found in parent compartment {} in tenancy {}\n\n".format(
            child_compartment_name,
            parent_compartment.name,
            config["tenancy"]
        ))
        raise RuntimeWarning("WARNING! - Compartment not found")
    elif option == "--OCID":
        print(child_compartment.id)
    elif option == "--NAME":
        print(child_compartment.name)
    elif option == "--DATE-CREATED":
        print(child_compartment.time_created)
    elif option == "--JSON":
        print(child_compartment)
        
    elif len(option) == 0:

        header = [
            "COMPARTMENT",
            "DESCRIPTION",
            "LIFECYCLE STATE"
        ]
        data_rows = [[
            child_compartment_name,
            child_compartment.description,
            child_compartment.lifecycle_state
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("OCID\t\t" + child_compartment.id + "\n\n")

    else:
        print(
            "\n\nIncorrect option. Correct options are:\n\n" +
            "\t--ocid\t\tPrints the Oracle Cloud Identifier for this object\n" +
            "\t--name\t\tPrints the name of the compartment\n" +
            "\t--time-created\tPrints the date the compartment was created on\n" +
            "\t--json\t\tPrint in JSON format and surpress other output\n\n"
        )
        raise RuntimeError("EXCEPTION! - Invalid option")


