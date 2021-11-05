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

Pagination must be used to fetch custom images. See
 https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.list_images.
 and https://github.com/oracle/oci-python-sdk/blob/aeaadacd93742e5e7e15fd342c68caad8d94b240/tests/unit/test_response.py#L8 
 

'''
# required system modules
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.compute import GetImages
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient

copywrite()
sleep(2)
if len(sys.argv) != 5:
    print(
        "\n\nOci-GetImage : Usage\n" +
        "Oci-GetImage.py [parent compartment] [child compartment] [image name] [region]\n\n" +
        "Use Case Example 1 - List all images by name available within the specified compartment:\n" +
        "\tOci-GetImage.py admin_comp bak_comp list_all_images 'us-ashburn-1'\n" +
        "Use Case Example 2 - List a specific image in JSON format within the specified compartment:\n" +
        "\tOci-GetImage.py admin_comp bak_comp 'Oracle-Linux-8.4-Gen2-GPU-2021.10.20-0' 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Incorrect usage")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
image_string                = sys.argv[3]
region                      = sys.argv[4]


# instiate the environment and validate that the specified region exists
config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config)
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

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client = ComputeClient(config) # builds the network client method, required to manage network resources

# get the parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found within tenancy " + config["tenancy"]
)

# get the child compartment
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

# get image data from the compartment within the specified region
images = GetImages(
    compute_client,
    child_compartment.id)
images.populate_image_list()

header = [
    "IMAGE NAME",
    "IMAGE OCID"
]

data_rows = []

if image_string == "list_all_images":
    for image in images.image_list:
        data_row = [
            image[0],
            image[1]
        ]
        data_rows.append
# print(images.image_list)        
    print(tabulate(images.image_list, headers = header, tablefmt = "grid"))
else:
    print(images.return_image(image_string))