#!/bin/python3

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
# required system modules
from detect_delimiter import detect
import pandas as pd
import os.path
import sys
from datetime import datetime
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import return_availability_domain
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.compute import check_for_vm
from lib.compute import GetImages
from lib.compute import GetInstance
from lib.compute import LaunchVmInstance
from lib.vcns import GetVirtualCloudNetworks
from lib.subnets import GetPrivateIP
from lib.subnets import GetSubnet
from oci.config import from_file

# required OCI modules
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import ComputeClientCompositeOperations
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.core.models import CreateVnicDetails
from oci.core.models import InstanceSourceDetails
from oci.core.models import InstanceSourceViaImageDetails
from oci.core.models import LaunchInstanceDetails
from oci.core.models import LaunchInstanceShapeConfigDetails

copywrite()
sleep(2)
if len(sys.argv) != 5:
    print(
        "\n\nOci-AddWindowsFromCsvFile.py : Usage\n\n" +
        "Oci-AddWindowsFromCsvFile.py [parent compartment] [child compartment] [region] [csv import file]\n\n" +
        "Use case example adds VM instances to the specified child compartment within the specified region:\n" +
        "\tOci-AddWindowsFromCsvFile.py admin_comp web_comp 'us-phoenix-1' drtest_vms_to_build.csv\n\n" +
        "WARNING! This program will not create duplicate VM instances. This means your CSV input file must\n" +
        "contain unique names for each instance within the specified compartment/region in order for each\n" +
        "respective VM instance to be launched.\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("EXCEPTION! Incorrect usage")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
region                          = sys.argv[3]
vm_import_csv_file_name         = sys.argv[4]

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


def get_image_id(
            compartments,
            image_compartment_name,
            image_name):
    '''
    Function searches all compartment objects for image_compartment_name,
    then instiates the class GetImages to retrieve the image object. It
    returns the image OCID or None if no image is found. This function is
    to be run in __main__
    '''
    for compartment in compartments:
        if compartment.name == image_compartment_name:
            images = GetImages(
                compute_client,
                compartment.id)
            images.populate_image_list()
            image = images.return_image(image_name)
            return image.id


# end function get_image_id()

def import_csv_to_dataframe(
    import_file):
    '''
    This function uses pandas to retrieve the data in the CSV rule export file into
    a dataframe. It returns the dataframe to the calling code. For example, if the
    a record contains:
        Rule Description;Protocol (ICMP/ICMPv6/TCP/UDP);Is Stateless (False/True);Source;Source Type;Destination;Destination Type;ICMP Type;ICMP Code;Source TCP Maximum Port;Source TCP Minimum Port;Destination TCP Maximum Port;Destination TCP Minimum Port;Source UDP Maximum Port;Source UDP Minimum Port;Destination UDP Maximum Port;Destination UDP Minimum UDP Port
        Sample rule permits all Inbound TCP traffic from tenancy;TCP;10.1.0.0/20;CIDR_BLOCK;;;;;;;;;;
        Sample rule permits all Inbound TCP traffic from tenancy;TCP;10.1.0.0/20;CIDR_BLOCK;;;;;;;;;;

    And you wish to read the second field in the 1st row, simply doing this will retrieve the data:
    
    my_data = rules.iloc[1,1]
    
    The contents of my_data now are "TCP"

    WARNING!
    This function must be called from __main__
    pandas must be loaded

    WARNING! This function requires the use of detect from the detect_delimiter module.
    The module was developed during python2.x days but has been tested up to python
    version 3.8.5. Versions after this should be tested during the codebase deployment.
    See https://pypi.org/project/detect-delimiter/ 
    
    To later extract specific values from the datafrom, use the iloc method.
    See the pandas user guide for more information at
    https://pandas.pydata.org/docs/user_guide/10min.html#object-creation
    '''
    
    # determine the delimiter with detect, see
    # https://pypi.org/project/detect-delimiter/
    with open(import_file) as myfile:
        firstline = myfile.readline()
    myfile.close()
    delimiter = detect(firstline)
    # start by opening the CSV import file for reading
    records = pd.read_csv(import_file,
                         sep = delimiter)
    return records

# end function import_csv_to_dataframe()

def return_host_record(cntr):
    my_host_details     = None
    my_allowed_shapes   = [
        "VM.Standard2.1",
        "WM.Standard2.2",
        "VM.Standard2.4",
        "VM.Standard2.8",
        "VM.Standard2.16",
        "VM.Standard2.24"]

    # get virtual cloud network data for the VM
    virtual_networks = GetVirtualCloudNetworks(
        network_client,
        child_compartment.id,
        vm_list.iloc[cntr][1])
    virtual_networks.populate_virtual_cloud_networks()
    virtual_cloud_network = virtual_networks.return_virtual_cloud_network()
    error_trap_resource_not_found(
        virtual_cloud_network,
        "Virtual cloud network " + vm_list.iloc[cntr][1] + " not found in compartment " + child_compartment_name + " for VM creation."
    )
    sleep(1)
    # get the subnet data
    subnets = GetSubnet(
        network_client,
        child_compartment.id,
        virtual_cloud_network.id,
        vm_list.iloc[cntr][2])
    subnets.populate_subnets()
    subnet = subnets.return_subnet()
    error_trap_resource_not_found(
        subnet,
        "Subnetwork " + vm_list.iloc[cntr][2] + " not found within virtual cloud network " + vm_list.iloc[cntr][1] + " for vm creation."
    )
    # check to see if the VM exists, if it does, print an error and do not return a record,
    # otherwise, return the data to the calling code.
    vm_name = vm_list.iloc[cntr][0]
    # print(vm_name)
    if check_for_vm(
        compute_client,
        child_compartment.id,
        vm_name):
        print("VM {} already present in compartment {} and will be skipped. Duplicate VMs not permitted.\n".format(
            vm_name,
            child_compartment_name))
    else:
        # instiate the host dictionary object
        my_host_details = host_details
        my_host_details["instance_name"] = vm_list.iloc[cntr][0]
        my_host_details["instance_details"]["availability_domain"] = \
            return_availability_domain(
                identity_client,
                child_compartment.id,
                vm_list.iloc[cntr][3])
        sleep(1) # necessary to make sure we do not send too many requests to REST API service at once
        if str(vm_list.iloc[cntr][4]).upper() == "TRUE":
            my_host_details["network_properties"]["assign_public_ip"] = True
        else:
            my_host_details["network_properties"]["assign_public_ip"] = False
        my_host_details["network_properties"]["private_ip"] = vm_list.iloc[cntr][5]
        my_host_details["network_properties"]["display_name"] = vm_name + "_vnic_00"
        my_host_details["network_properties"]["vcn_name"] = vm_list.iloc[cntr][1]
        my_host_details["network_properties"]["subnet_name"] = vm_list.iloc[cntr][2]
        my_host_details["image_id"] = get_image_id(
                child_compartments.child_compartments,
                vm_list.iloc[cntr][7],
                vm_list.iloc[cntr][6])
        if int(vm_list.iloc[cntr][8]) >=256:
            my_host_details["boot_volume_size_in_gbs"] = int(vm_list.iloc[cntr][8])
        else:
            raise RuntimeWarning("WARNING! Image size specified in record is less than 256Gbyte in size. Disk size for a Windows image must be at least 256Gbyte in size.")
        my_host_details["shape_properties"]["shape"] = vm_list.iloc[cntr][9]
        my_host_details["instance_details"]["ssh_key_file"] = "NOT_USED_FOR_WINDOWS_IMAGES"
        if my_host_details["shape_properties"]["shape"] not in my_allowed_shapes:
            print(
                "\n\nWARNING! Invalid shape for a Windows VM instance specified in record. Allowed shapes are:\n\n" +
                "\tSHAPE            \n" +
                "\t=================\n"
            )
            for shape in my_allowed_shapes:
                print("\t" + shape)
            print(
                "\n\nPlease visit https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm\n" +
                "and review 'Standard Shapes' in the document. Then update your CSV import file accordingly.\n\n"
                )
            raise RuntimeWarning("WARNING! Illegal shape for Windows iamge.")
        
        return my_host_details

# end function return_host_record()

# main program body
# We want this program to be called from the shell, or from a forked process. If not
# __main__, then raise an exception.
if __name__ != "__main__":

    raise RuntimeError("EXCEPTION! - Program may not be called by another program.")


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

# import the CSV file
if not os.path.exists(vm_import_csv_file_name):
    raise RuntimeWarning("WARNING! Import file not found")
vm_list = import_csv_to_dataframe(vm_import_csv_file_name)

# start running through the logic to create the VM instances.

count = len(vm_list)
cntr  = 0
print("\n\nStarting the job to create VM instances from a CSV import file as of {}......\n\n".format(
    datetime.now()
))
while cntr < count:

    # insert the host record into the dictionary object
    print("Reading CSV record {} and checking for the VM instance and source VM image details......".format(
        cntr+1
    ))
    my_host = return_host_record(cntr)

#    print("Check completed")
    if my_host is None:
        # do nothing if the VM instance is already present
        pass
    else:
        # # get the virtual cloud network and subnet data for creating the VM object
        print("Getting the virtual cloud network and subnet details......")
        virtual_clouud_networks = GetVirtualCloudNetworks(
            network_client,
            child_compartment.id,
            my_host["network_properties"]["vcn_name"])
        virtual_clouud_networks.populate_virtual_cloud_networks()
        virtual_clouud_network = virtual_clouud_networks.return_virtual_cloud_network()
        error_trap_resource_not_found(
            virtual_clouud_network,
            "Virtual cloud network requested in CSV record not found in compartment " + child_compartment_name
        )
        subnetworks = GetSubnet(
            network_client,
            child_compartment.id,
            virtual_clouud_network.id,
            my_host["network_properties"]["subnet_name"])
        subnetworks.populate_subnets()
        subnet = subnetworks.return_subnet()
        error_trap_resource_not_found(
            subnet,
            "Subnetwork requested for in CSV record not found in compartment " + child_compartment_name
        )
    
        # look for duplicate IP addresses, raise warning if found
        private_ip_addresses = GetPrivateIP(
            network_client,
            subnet.id
        )
        private_ip_addresses.populate_ip_addresses()
        if private_ip_addresses.is_dup_ip(my_host["network_properties"]["private_ip"]):
            warning_beep(1)
            print("\n\nWARNING! IP address {} already assigned to subnet {}.\n".format(
               my_host["network_properties"]["private_ip"],
               subnet.display_name 
            ))
            print("Please correct your entry for host {} in the CSV file and try again.\n".format(
              my_host["network_properties"]["private_ip"]  
            ))
            raise RuntimeWarning("DUPLICATE IP ADDRESS FOUND.")

        # # instiate the class for launching the VM and run the methods to prepare the class object data
        # # for VM creation.
        print("Recording the data to memory necessary to create the VM instance......\n\n")
        vm_instance = LaunchVmInstance(
            compute_composite_client,
            CreateVnicDetails,
            InstanceSourceDetails,
            InstanceSourceViaImageDetails,
            LaunchInstanceDetails,
            LaunchInstanceShapeConfigDetails,
            child_compartment.id,
            subnet.id,
            my_host)
        vm_instance.build_vnic_details()
        sleep(1)
        vm_instance.build_instance_image_details()
        sleep(1)
        vm_instance.build_shape()
        sleep(1)
        vm_instance.build_launch_instance_details()
        sleep(1)
    
        # # create the instance
        print("######################################################################\n")
        print("\n\nVM instance {} ready for launching on subnet {}\n\n".format(
            my_host["instance_name"],
            my_host["network_properties"]["subnet_name"]))
        print("\n\nCreating the instance now. This will take several minutes based\n" +
              "on the complexity of the source image and the VM instance size......\n\n")
        results = vm_instance.launch_instance_and_wait_for_state()
        print("Instance created, here are the results\n\n")
        print(results)
        print("\n\nEND OF RESULTS HERE\n\n")
        print("######################################################################\n")



    cntr += 1

print("\n\nJob is completed and {} VMs have been successfully created. Please examine".format(cntr))
print("the job output for details and for any potential errors.\n\n")
print("Job ending as of {}\n\n".format(
    datetime.now()
))

# end while cntr < count








