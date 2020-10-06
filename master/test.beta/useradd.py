#!/Users/henrywojteczko/bin/python
# Modify the above entry to point to the client's python3 virtual environment prior to execution

'''
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
import oci
import os.path
import sys

if len(sys.argv) != 5: # ARGS PLUS COMMAND
    raise RuntimeError('\n\n\nInvalid number of arguments provided to the script.\n'
                        'Correct Usage: useradd.py [username] [user description] [user email address] [default user group ID]\n'
                        'Please try again.\n')


username            = sys.argv[1]
UsrEmail            = sys.argv[2]
UsrDescription      = sys.argv[3]
UsrGroup_id         = sys.argv[4]



# functions
def UserAdd(identity_client, tenancy, myUserName, myDescription, myEmail, myGroup_id):
    user_details = oci.identity.models.CreateUserDetails(
        compartment_id = tenancy,
        name = myUserName,
        description = myDescription,
        email = myEmail
    )
    print(user_details)
    results = identity_client.create_user(
        user_details
    ).data
    print("User "+results.name+" created\n\n"
          "Now setting the user's one time use password and adding the user to the group......\n\n\n")
    newpassword = identity_client.create_or_reset_ui_password(
        user_id = results.id
    ).data
    user_group_details = oci.identity.models.AddUserToGroupDetails(
        user_id  = results.id,
        group_id = myGroup_id
    )
#    print(user_group_details)

    group_add_results = identity_client.add_user_to_group(
        user_group_details
    ).data
    print(group_add_results)

    print("User "+results.name+" one time user password set to \n\n\n"+newpassword.password+"\n\n\n"
          "Please make a note of the password and provide to user with URL to login to the Oracle cloud.\n\n"
          "Program ending\n")


    


# end function UserAdd

# Default config file and profile
config = oci.config.from_file()
tenancy = config["tenancy"]

identity_client = oci.identity.IdentityClient(config)


UserAdd(identity_client, tenancy, username, UsrDescription, UsrEmail, UsrGroup_id)
