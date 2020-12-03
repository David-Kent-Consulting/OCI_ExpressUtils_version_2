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
from lib.compartments import del_compartment
from lib.general import warning_beep
import os.path
import sys

option = []
compartment_name = None
#print(len(sys.argv))
if len(sys.argv) < 2 or len(sys.argv) > 3: # ARGS PLUS COMMAND
    print(
        "Oci-DeleteParentCompartment.py : Correct Usage\n\n" +
        "Oci-DeleteParentCompartment.py [parent compartment name] [optional argument] \n\n" +
        "Use case example deletes the parent compartment object that is subordinate\n" +
        "to the root tenancy compartment with the force option. Omit --force should you desire to be prompted.\n\n" +
        "Oci-DeleteParentCompartment.py admin_comp --force\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n"
        )

    raise RuntimeError(
        "EXCEPTION! Incorrect usage."
    )
elif len(sys.argv) == 3:
    option = sys.argv[2].upper()
    process_option = True
parent_compartment_name = sys.argv[1]

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
# this initiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# We create the method my_compartments from the DKC API 
my_compartments = lib.compartments.GetParentCompartments(parent_compartment_name, config, identity_client)
my_compartments.populate_compartments()

#print(my_compartments.return_parent_compartment())
compartment_name = my_compartments.return_parent_compartment()
#print(compartment_name.name)
if compartment_name is None:
    print("Compartment name {} not found in tenancy {}\n".format(parent_compartment_name, config["tenancy"]))
    print("Please try again with a correct compartment name.\n")
    raise RuntimeError("EXCEPTION! Compartment not found")
elif option == "--FORCE":
    # call the above function to create the compartment
    results = del_compartment(identity_client, my_compartments.return_parent_compartment().id)
    print("Parent compartment {} remove request submitted.\n".format(parent_compartment_name))
elif len(option) >= 1:
    print(
        "The only valid option for this utility is --force\n" +
        "Please try again.\n"
        )
    raise RuntimeWarning("WARNING! - Invalid option")
else:
    warning_beep(6)
    print(
    "ARE YOU SURE THAT YOU WANT TO DO THIS?\n\n"
    )
    if "YES" == (input("Enter 'YES' to proceed to remove parent compartment {}, or any other key to exit\n".format(parent_compartment_name))):
        results = del_compartment(identity_client, my_compartments.return_parent_compartment().id)
        print("Parent compartment {} remove request submitted.\n".format(parent_compartment_name))
    else:
        print("Oci-DeleteParentCompartment aborted per user request\n")

