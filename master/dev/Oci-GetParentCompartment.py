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


import oci
import lib.compartments
import os.path
import sys

option = []


# end check_for_duplicates

# We require the parent compartment name for this tool. An option can be passed as the second
# argument.
if len(sys.argv) < 2 or len(sys.argv) > 3: # ARGS PLUS COMMAND
    print(
        "Oci-GetParentCompartment.py : Correct Usage\n\n" +
        "Oci-GetParentCompartment.py [parent compartment name] [optional argument]\n\n" +
        "Use case example 1 prints just the parent compartment object that is subordinate\n" +
        "to the root tenancy compartment.\n\n" +
        "Oci-GetParentCompartment.py admin_comp\n\n" +
        "Use case example 2 prints all parent compartments that are subordinate to the\n" +
        "root tenancy compartment\n\n" +
        "Oci-GetParentCompartment.py list_all_parent_compartments\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n"
        )

    raise RuntimeError(
        "EXCEPTION! Incorrect usage."
    )
if len(sys.argv) == 3:
    option = sys.argv[2]
parent_compartment_name = sys.argv[1]

# initialize the environment

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
# this initiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# We create the method my_compartments from the DKC API 
my_compartments = lib.compartments.GetParentCompartments(parent_compartment_name, config, identity_client)
my_compartments.populate_compartments()

compartment_name = my_compartments.return_parent_compartment()

if parent_compartment_name.upper() == "LIST_ALL_PARENT_COMPARTMENTS":
    print(my_compartments.parent_compartments)
elif compartment_name is None:
    print("Compartment name {} not found in tenancy {}".format(parent_compartment_name, config["tenancy"]))
    exit(1)
elif len(option) == 0:
    print(my_compartments.return_parent_compartment())
elif option == "--ocid":
    print(my_compartments.return_parent_compartment().id)
elif option == "--name":
    print(my_compartments.return_parent_compartment().name)
elif option == "--time-created":
    print(my_compartments.return_parent_compartment().time_created)
else:
    print(
        "Incorrect option. Correct options are:\n\n" +
        "\t--ocid\t\t: prints the Oracle Cloud Identifier for this object\n" +
        "\t--name\t\t: prints the name of the compartment\n" +
        "\t--time-created\t\: prints the date the compartment was created on\n\n"
    )
