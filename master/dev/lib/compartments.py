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

from oci import config
from oci import identity
import oci




class GetParentCompartments:
    '''
    method GetParentCompartments:
    
    This method pulls all parent compartment data using the OCI API and stores to as a dict object
    all compartments that are active. Call like:
         "my_compartments = GetParentCompartment("compartment_name", config, identity_client)

    arguments:

        compartment_name:
            The name of the compartment that is the parent that is the child of the root
            compartment
        config:
            dict object created on the calling program as in "config = oci.config.from_file()"
        identity_client:
            a class object created in the calling program as in
            "identity_client = oci.identity.IdentityClient(config)"

    The config object is created using oci.config.from_file. Your class object must be populated
    only one time to be of use. You may not run a populate a second time. It is notable that the
    entire codebase is dependent on having the parent compartment object from the root
    compartment (tenancy). If a different parent is required, create a new object from this class
    and populate.

    To return the parent compartment name and tenancy, simply print the object. To return the
    parent object, simply call the method after populated as in:
        my_compartments.return_parent_compartment()


    method GetChildCompartments:
    Similar to GetParentCompartments, gets the children from the supplied parent compartment object

    Arguments:

        parent_compartment_id:
            The parent compartment OCID
        config:
           dict object created on the calling program as in "config = oci.config.from_file()"
        identity_client:
            a class object created in the calling program as in
            "identity_client = oci.identity.IdentityClient(config)"

    Method populate_compartments(self)
        This method will read all parent compartments from the root compartment and will append
        self.parent_compartments with all compartments that have an 'ACTIVE' lifecycle state

    Method return_parent_compartment(self)
        This method parses through parent_compartments and returns the parent compartment object
        with the name that matches self.parent_compartment_name if found.
'''
    def __init__(self,parent_compartment_name, config, identity_client):
        self.parent_compartment_name = parent_compartment_name
        self.parent_compartments = []
        self.config = config
        self.identity_client = identity_client
        
    def populate_compartments(self):
        if len(self.parent_compartments) != 0:
            return None
        
        results = self.identity_client.list_compartments(self.config["tenancy"])
        for item in results.data:
            if item.lifecycle_state != 'DELETED':
                if item.lifecycle_state != 'DELETING':
                    self.parent_compartments.append(item)

    def return_all_parent_compartments(self):
        
        if len(self.parent_compartments) == 0:
            return None
        else:
            return self.parent_compartments
                
    def return_parent_compartment(self):

        if len(self.parent_compartments) == 0:
            return None
        else:
            for item in self.parent_compartments:
                if item.name == self.parent_compartment_name:
                    return item
    
    def __str__(self):
        return "The parent compartment name is " + self.parent_compartment_name + " in tenancy " \
                + self.config["tenancy"]

# end class GetParentCompartments

class GetChildCompartments:
    '''
    This class operates similar to GetParentCompartments, except that it operates from the parent
    compartment object ID provided to it rather than the root compartment ID. It also has methods
    that returns all child compartments, or a select child compartment, if present in child_compartments.
    '''
    def __init__(self, parent_compartment_id, child_compartment_name, identity_client):
        self.parent_compartment_id = parent_compartment_id
        self.child_compartment_name = child_compartment_name
        self.identity_client = identity_client
        self.child_compartments = []
    
    def populate_compartments(self):

        if len(self.child_compartments) != 0:
            return None
        results = self.identity_client.list_compartments(self.parent_compartment_id)
        for item in results.data:
            if item.lifecycle_state != 'DELETED':
                if item.lifecycle_state != 'DELETING':
                    self.child_compartments.append(item)
    
    def return_all_child_compartments(self):
        if len(self.child_compartments) == 0:
            return None
        else:
            return self.child_compartments

    def return_child_compartment(self):
        if len(self.child_compartments) == 0:
            return None
        else:
            for item in self.child_compartments:
                if item.name == self.child_compartment_name:
                    return item
                
    def __str__(self):
        return "The child compartment name is " + self.child_compartment_name
                
# end GetChildCompartments


def add_compartment(parent_compartment_id, identity_client, new_compartment_name, description):
    '''
    This function creates a compartment. It does not check for duplicates. You should check for
    duplicates and handle as an exception with your code. The parent compartment id is supplied,
    along with the name of the new compaertment to create and the description. The function
    returns the results. Your code has to manage the exception if results is returned as a null
    value.
    '''
    results = None
    # the following creates a dict object that pre-defines the details required
    # to create the compartment.
    compartment_details = oci.identity.models.CreateCompartmentDetails (
        compartment_id = parent_compartment_id,
        name = new_compartment_name,
        description = description
    )
    # print(compartment_details)
    # exit
    # now we call the method create_compartment and pass the dict object compartment_details
    # to associated with the key word create_compartment_details. This is what the REST API
    # service is expecting. We opt to not send any tags.
    results = identity_client.create_compartment(
        create_compartment_details  = compartment_details
    ).data

    return results
# end add_compartment()

def del_compartment(identity_client, compartment_id):
    '''
    This function creates a compartment. It does not check for duplicates. You should check for
    duplicates and handle as an exception with your code. The parent compartment id is supplied,
    along with the name of the new compaertment to create and the description. The function
    returns the results. Your code has to manage the exception if results is returned as a null
    value.
    '''
    # print(compartment_id)
    results = identity_client.delete_compartment(
        compartment_id = compartment_id
    )
    # now we call the method create_compartment and pass the dict object compartment_details
    # to associated with the key word create_compartment_details. This is what the REST API
    # service is expecting. We opt to not send any tags.
    

    return results

# end del_compartment()

# code to test
'''
config = oci.config.from_file()
identity_client = oci.identity.IdentityClient(config)

my_compartments = lib.compartments.GetParentCompartments("admin_comp", config, identity_client)
# print(my_compartments)
my_compartments.populate_compartments()
# for item in my_compartments.parent_compartments:
#     print(item.name)

my_parent_compartment = my_compartments.return_parent_compartment()
# print(my_parent_compartment)

my_child_compartments = GetChildCompartments(my_parent_compartment)
# print(my_child_compartments)
my_child_compartments.populate_compartments()
testvar = my_child_compartments.return_all_child_compartments()
# print(testvar)
testvar = my_child_compartments.return_child_compartment("auto_comp")
# add_compartment(config["tenancy"], "test_compartment", "This is a test")
#testvar = add_compartment(config["tenancy"], "test_compartment", "this is a test compartment")
check_for_duplicates(child_compartments, "admin_comp") # returns true if duplicate, false if not

print(testvar)
'''