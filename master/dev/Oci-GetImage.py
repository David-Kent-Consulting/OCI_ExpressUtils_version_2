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

import os.path
import sys
from time import sleep
from lib.general import error_trap_resource_not_found
from lib.compute import GetImages
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.vcns import GetVirtualCloudNetworks
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient

if len(sys.argv) < 5 or len(sys.argv) > 6:
    print(
        "\n\nOci-GetImage : Usage\n" +
        "Oci-GetImage.py [parent compartment] [child compartment] [image name] [region] [optional argument]\n\n" +
        "Use Case Example 1 - List all images by name available within the specified compartment:\n" +
        "\tOci-GetImage.py admin_comp bak_comp list_all_images_in_compartment 'us-ashburn-1' --name\n" +
        "Use case example 2 - List information about a specific image name:\n" +
        "\tOci-GetImage.py admin_comp auto_comp 'AnsibleCLI_Image_2.9.9_08-oct-2020' 'us-ashburn-1' \n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("WARNING! - Incorrect usage")

parent_compartment_name     = sys.argv[1]
child_compartment_name      = sys.argv[2]
image_string                = sys.argv[3]
region                      = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()

# instiate the environment
config = from_file() # gets ~./.oci/config and reads to the object
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

# run through the logic for list all images
if image_string.upper() == "LIST_ALL_IMAGES_IN_COMPARTMENT" and len(sys.argv) == 5:
    print("IMAGE NAME\t\t\t\t\t\t\tIMAGE OCID\n\n")
    for image in images.image_list:
        print(image[0] + "\t\t" + image[1])
elif image_string.upper() == "LIST_ALL_IMAGES_IN_COMPARTMENT" and option == "--NAME":
    print("IMAGE NAME\n\n")
    for image in images.image_list:
        print(image[0])
elif image_string.upper() == "LIST_ALL_IMAGES_IN_COMPARTMENT" and option == "--WINDOWS":
    print("IMAGE NAME\n\n")
    for image in images.image_list:
        image_object = images.return_image(image[0])
        if image_object.operating_system == "Windows":
            print(image_object)
elif image_string.upper() == "LIST_ALL_IMAGES_IN_COMPARTMENT" and option == "--LINUX":
    print("IMAGE NAME\n\n")
    for image in images.image_list:    
        image_object = images.return_image(image[0])
        if image_object.operating_system != "Windows":
            print(image_object)

# run through the logic for listing a specific image's detail
else:
    image_object = images.return_image(image_string)
    error_trap_resource_not_found(
        image_object,
        "Image " + image_string + " not found within child compartment " + child_compartment_name
    )
    # no options provided, print all object details
    if len(sys.argv) == 5:
        print(image_object)
    elif option == "--OCID":
        print(image_object.id)
    elif option == "--NAME":
        print(image_object.display_name)
    elif option == "--LAUNCH-MODE":
        print(image_object.launch_mode)
    elif option == "LAUNCH-OPTIONS":
        print(image_object.launch_options)
    elif option == "--OPERATING-SYSTEM":
        print(image_object.operating_system)
    elif option == "--VERSION":
        print(image_object.operating_system_version)
    else:
        print(
            "\n\nINVALID OPTION - Valid options are:\n\n" +
            "\t--ocid\t\t\tPrint the OCID of the image resource\n" +
            "\t--name\t\t\tPrint the name of the image resource\n" +
            "\t--launch-mode\t\tPrint the launch mode required for use of the image resource\n" +
            "\t--launch-options\tPrint the launch options details for the image resource\n" +
            "\t--operating system\tPrint the image resource operating system type\n" +
            "\t--version\t\tPrint the version of the operating system of the image resource\n"
            )
        
