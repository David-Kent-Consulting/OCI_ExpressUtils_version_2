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
from lib.compartments import add_compartment
import os.path
import sys

option = []
if len(sys.argv) != 3: # ARGS PLUS COMMAND
    print(
        "Oci-AddParentCompartment.py : Correct Usage\n\n" +
        "Oci-AddParentCompartment.py [parent compartment name] [description] \n\n" +
        "Use case example adds the parent compartment object that is subordinate\n" +
        "to the root tenancy compartment.\n\n" +
        "Oci-AddParentCompartment.py admin_comp 'This is the parent admin compartment'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n"
        )

    raise RuntimeError(
        "EXCEPTION! Incorrect usage."
    )
elif len(sys.argv) == 3:
    option = sys.argv[2].upper()
    description = sys.argv[2]
    process_option = True
parent_compartment_name = sys.argv[1]


# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
# this initiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# We create the method my_compartments from the DKC API 
my_compartments = lib.compartments.GetParentCompartments(parent_compartment_name, config, identity_client)
my_compartments.populate_compartments()
# check to see if a duplicate exists, if found, print a message and exit with rc of 1

compartment_name = my_compartments.return_parent_compartment()
if compartment_name is None:
    results = add_compartment(config["tenancy"], identity_client, parent_compartment_name, description)
    print(results)
elif compartment_name.name == parent_compartment_name:
    print("Compartment name {} found in tenancy {}\n".format(parent_compartment_name, config["tenancy"]))
    print("Duplicate compartments are possible in OCI but are not recommended.")
    exit(1)
# else:
#     # call the above function to create the compartment
#     # results = add_compartment(config["tenancy"], parent_compartment_name, description)
#     # print(results)
#     print("It worked")
