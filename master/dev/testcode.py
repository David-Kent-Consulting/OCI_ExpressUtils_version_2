#!/Users/henrywojteczko/anaconda3/bin/python

#######################################################
### WARNING! WARNING! WARNING! WARNING! WARNING!    ###
###                                                 ###
### The python interpreter that matches the version ###
### installed with anaconda and pandas must be      ###
### loaded. Failure to do so will result in import  ###
### and runtime erroors.                            ###
###                                                 ###
### WARNING! WARNING! WARNING! WARNING! WARNING!    ###
#######################################################

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

Package requirements: Python 3.8.5 or later, conda, pandas.
Be certain your libpaths are correct for python otherwise pandas will not import.

'''

import pandas as pd
import os.path
import sys
from time import sleep
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import import_csv_to_dataframe
from lib.general import get_availability_domains
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import change_instance_name
from lib.compute import change_instance_shape
from lib.compute import GetImages
from lib.compute import GetInstance
from lib.compute import LaunchVmInstance
from lib.compute import stop_os_and_instance
from lib.compute import terminate_instance
from lib.vcns import GetVirtualCloudNetworks
from lib.subnets import GetSubnet
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import VirtualNetworkClient
from oci.core.models import CreateVnicDetails
from oci.core.models import InstanceSourceDetails
from oci.core.models import InstanceSourceViaImageDetails
from oci.core.models import LaunchInstanceDetails
from oci.core.models import LaunchInstanceShapeConfigDetails
from oci.core.models import UpdateInstanceShapeConfigDetails
from oci.core.models import UpdateInstanceDetails

parent_compartment_name = "admin_comp"
child_compartment_name  = "bas_comp"
virtual_cloud_network_name = "bas_vcn"
virtual_cloud_subnet_name  = "bas_sub"
region                  = "us-ashburn-1"
image_name = "DMZT01"

# dictionary object that will be passed to the class LaunchVmInstance
# image_id will be instiated after getting the image ID using 
# the class lib.compute.GetImages.

host_details = {
    "instance_name"       : "",
    "instance_details"    : {
        "availability_domain"    : "",
        "ssh_key_file"           : ""
    },
    "network_properties"  : {
        "assign_public_ip"    : None,
        "private_ip"          : "",
        "display_name"        : "",
        "vcn_name"            : "",
        "subnet_name"         : ""
    },
    "image_id"            : "",
    "boot_volume_size_in_gbs" : None,
    "shape_properties"    : {
        "shape"               : "",
        "memory_in_gbs"       : None,
        "ocpus"               : None
    }
}

# instiate the environment
config = from_file() # gets ~./.oci/config and reads to the object
config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
compute_client = ComputeClient(config) # builds the network client method, required to manage network resources
compute_composite_client = ComputeClientCompositeOperations(compute_client)
network_client = VirtualNetworkClient(config)

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

import_file = "bas_comp_vm_list.csv"
if not os.path.exists(import_file):
    raise RuntimeWarning("WARNING! File not found")

vm_list = import_csv_to_dataframe(import_file, ";")

def return_availability_domain(
    compartment_id,
    ad_number):
    
    if ad_number > 0 and ad_number <= 3:
        availability_domains = get_availability_domains(
            identity_client,
            compartment_id)
    
        return availability_domains[ad_number - 1].name
    else:
        return None


def check_for_vm(
    vm_name):
    '''
    Function returns boolean True if the vm instance is found, otherwise it returns false
    '''
    vm_instances = GetInstance(
        compute_client,
        compute_composite_client,
        child_compartment.id,
        vm_name
    )
    vm_instances.populate_instances()
    vm_instance = vm_instances.return_instance()
    if vm_instance is not None:
        return True
    else:
        return False


def get_image_id(compartments,
              image_compartment_name,
              image_name):
    
    for compartment in compartments:
        if compartment.name == image_compartment_name:
            images = GetImages(
                compute_client,
                compartment.id)
            images.populate_image_list()
            image = images.return_image(image_name)
            return image.id

def return_host_record(cntr):
    my_host_details = None
    # get virtual cloud network data for the VM
    virtual_networks = GetVirtualCloudNetworks(
        network_client,
        child_compartment.id,
        vm_list.iloc[cntr][1])
    virtual_networks.populate_virtual_cloud_networks()
    virtual_cloud_network = virtual_networks.return_virtual_cloud_network()
    sleep(1)
    # get the subnet data
    subnets = GetSubnet(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        vm_list.iloc[cntr][2])
    subnets.populate_subnets()
    subnet = subnets.return_subnet()
    # check to see if the VM exists
    vm_name = vm_list.iloc[cntr][0]
    # print(vm_name)
    if check_for_vm(vm_name):
        print("VM {} already present in compartment {}. Duplicate VMs not permitted.\n".format(
            vm_name,
            child_compartment_name))
    else:
        # instiate the host dictionary object
        print("test")
        my_host_details = host_details
        my_host_details["instance_name"] = vm_list.iloc[cntr][0]
        my_host_details["instance_details"]["availability_domain"] = \
             return_availability_domain(
                 child_compartment.id,
                 vm_list.iloc[cntr][3])
        my_host_details["instance_details"]["ssh_key_file"] = vm_list.iloc[cntr][4]
        if str(vm_list.iloc[cntr][5]).upper() == "TRUE":
            my_host_details["network_properties"]["assign_public_ip"] = True
        else:
            my_host_details["network_properties"]["assign_public_ip"] = False
        my_host_details["network_properties"]["private_ip"] = vm_list.iloc[cntr][6]
        my_host_details["network_properties"]["display_name"] = vm_name + "_vnic_00"
        my_host_details["network_properties"]["vcn_name"] = vm_list.iloc[cntr][1]
        my_host_details["network_properties"]["subnet_name"] = vm_list.iloc[cntr][2]
        my_host_details["image_id"] = get_image_id(child_compartments.child_compartments,
                  vm_list.iloc[cntr][8],
                  vm_list.iloc[cntr][7])
        my_host_details["boot_volume_size_in_gbs"] = int(vm_list.iloc[cntr][9])
        my_host_details["shape_properties"]["shape"] = vm_list.iloc[cntr][10]
        my_host_details["shape_properties"]["memory_in_gbs"] = int(vm_list.iloc[cntr][11])
        my_host_details["shape_properties"]["ocpus"] = int(vm_list.iloc[cntr][12])
        # print(my_host_details)
        return my_host_details

count = len(vm_list)
cntr = 0

while cntr < count:
    my_host = (return_host_record(cntr))
    print(my_host)
    if my_host is None:
        break

    
    # virtual_clouud_networks = GetVirtualCloudNetworks(
    #     network_client,
    #     child_compartment.id,
    #     my_host["network_properties"]["vcn_name"])
    # virtual_clouud_networks.populate_virtual_cloud_networks()
    # virtual_clouud_network = virtual_clouud_networks.return_virtual_cloud_network()
    # print(virtual_clouud_network)
    
    # subnetworks = GetSubnet(
    #     network_client,
    #     child_compartment.id,
    #     virtual_clouud_network.id,
    #     my_host["network_properties"]["subnet_name"])
    # subnetworks.populate_subnets()
    # subnet = subnetworks.return_subnet()
    # print(subnet)
    # print("\n\n")
    
    # vm_instance = LaunchVmInstance(
    #     compute_composite_client,
    #     CreateVnicDetails,
    #     InstanceSourceDetails,
    #     InstanceSourceViaImageDetails,
    #     LaunchInstanceDetails,
    #     LaunchInstanceShapeConfigDetails,
    #     child_compartment.id,
    #     subnet.id,
    #     my_host)
    # print(vm_instance)

    # del(my_host)
    # del(virtual_clouud_networks)
    # del(virtual_clouud_network)
    # del(subnet)
    cntr += 1
