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
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.compartments import del_compartment
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.general import warning_beep

# requiered OCI modules
import oci




option = []

copywrite()
sleep(2)
# We require the parent compartment name for this tool. An option can be passed as the second
# argument.
if len(sys.argv) < 3 or len(sys.argv) > 4: # ARGS PLUS COMMAND
    print(
        "\n\nOci-DeleteChildCompartment.py : Correct Usage\n\n" +
        "Oci-DeleteChildCompartment.py [parent compartment name] [child compartment] [optional argument]\n\n" +
        "Use case example deletes the child compartment object that is subordinate\n" +
        "to the supplied parent compartment.\n\n" +
        "Oci-DeleteChildCompartment.py admin_comp auto_comp --force\n\n" +

        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )

    raise RuntimeError(
        "EXCEPTION! Incorrect usage."
    )
if len(sys.argv) == 4:
    option = sys.argv[3]
parent_compartment_name = sys.argv[1]
child_compartment_name = sys.argv[2]

# initialize the environment

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
# this initiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# We create the method my_compartments from the DKC API 
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()

parent_compartment = parent_compartments.return_parent_compartment()

if parent_compartment is None:
    print("\n\nParent compartment name {} not found in tenancy {}".format(
        parent_compartment_name, config["tenancy"] + "\n" +
        "Please try again with a correct name.\n\n"
        )
    )
    raise RuntimeWarning("WARNING! - Compartment not found")

# # populate child compartments
child_compartments = GetChildCompartments(
    parent_compartments.return_parent_compartment().id,
    child_compartment_name,
    identity_client
    )
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()

if child_compartment is None:
    print(
        "\n\nChild compartment {} not found in parent compartment {} in tenancy {}\n".format(
            child_compartment_name,
            parent_compartment_name,
            config["tenancy"]
        ) +
        "Please try again with a correct child compartment name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Compartment not found")
elif option == "--force":
    results = del_compartment(
        identity_client,
        child_compartment.id
    )
    if results is None:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
    else:
        print("Child compartment {} remove request submitted.\n".format(child_compartment_name))
elif len(option) == 0:
    warning_beep(6)
    print(
    "ARE YOU SURE THAT YOU WANT TO DO THIS?\n\n"
    )
    if "YES" == (input("Enter 'YES' to proceed to remove child compartment {}, or any other key to exit\n".format(
        parent_compartment_name))):
        results = del_compartment(
            identity_client,
            child_compartment.id
        )
        if results is None:
            raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
        else:
            print("Child compartment {} remove request submitted.\n".format(child_compartment_name))
    else:
        print("Oci-DeleteChildCompartment aborted per user request\n")
else:
    print(
        "\n\nInvalid option. Correct option is --force\n\n"
    )
    raise RuntimeError("EXCEPTION! - Incorrect option")



