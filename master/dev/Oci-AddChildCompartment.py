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

# required OCI modules
import oci
import lib.compartments
from lib.compartments import add_compartment




option = []

copywrite()
sleep(2)
# end check_for_duplicates

# We require the parent compartment name for this tool. An option can be passed as the second
# argument.
if len(sys.argv) != 4: # ARGS PLUS COMMAND
    print(
        "\n\nOci-AddChildCompartment.py : Correct Usage\n\n" +
        "Oci-AddChildCompartment.py [parent compartment name] [child compartment] [compartment description]\n\n" +
        "Use case example adds the child compartment object that is subordinate\n" +
        "to the supplied parent compartment.\n\n" +
        "Oci-AddChildCompartment.py admin_comp auto_comp\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
        )

    raise RuntimeError(
        "EXCEPTION! Incorrect usage."
    )

parent_compartment_name = sys.argv[1]
child_compartment_name = sys.argv[2]
compartment_description = sys.argv[3]


# initialize the environment

# create the dict object config, which reads the ~./.oci/config file in this case
config = oci.config.from_file()
# this initiates the method identity_client from the API
identity_client = oci.identity.IdentityClient(config)
# We create the method my_compartments from the DKC API 
parent_compartments = lib.compartments.GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()

parent_compartment = parent_compartments.return_parent_compartment()

if parent_compartment is None:
    print("\n\nParent compartment name {} not found in tenancy {}".format(
        parent_compartment_name, config["tenancy"] + "\n" +
        "Please try again with a correct name.\n\n"
        )
    )
    raise RuntimeWarning("WARNING! - Compartment not found")

# populate child compartments
child_compartments = lib.compartments.GetChildCompartments(
    parent_compartments.return_parent_compartment().id,
    child_compartment_name,
    identity_client
    )
child_compartments.populate_compartments()

child_compartment = child_compartments.return_child_compartment()
if child_compartment is None:
    results = add_compartment(
        parent_compartment.id,
        identity_client,
        child_compartment_name,
        compartment_description
        )
    if results is None:
        raise RuntimeError("EXCEPTION! - UNKNOWN ERROR")
    else:
        print(results)
else:
    print(
        "\n\nChild compartment {} already found in parent compartment {} in tenancy {}\n".format(
            child_compartment_name,
            parent_compartment_name,
            config["tenancy"]
        ) +
        "Please try again with a non-existant child compartment name.\n\n"
    )
    raise RuntimeWarning("WARNING! - Compartment already exists")
