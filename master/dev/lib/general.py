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

from time import sleep
import os.path
import platform


class GetAlarms:
    '''
    
    The method populate_alarms returns all object of type AlarmSummary that are not TERMINATING or TERMINATED and
    stores the data in self.alarm_items.
    
    The method return_alarm returns the specified alarm item if found, otherwise it returns None.
    
    '''
    
    def __init__(
        self,
        monitoring_client,
        compartment_id):
        
        self.compartment_id      = compartment_id
        self.monitoring_client   = monitoring_client
        self.alarms              = []
        
    def populate_alarms(self):
        # populates the class
        
        if len(self.alarms) != 0:
            return False
        else:
            list_alarms_response = self.monitoring_client.list_alarms(
                compartment_id = self.compartment_id,
                sort_order = "ASC"
            )
            
            for a in list_alarms_response.data:
                if a.lifecycle_state == "ACTIVE":
                    self.alarms.append(a)
            
            while list_alarms_response.has_next_page:
                list_alarms_response = self.monitoring_client.list_alarms(
                    compartment_id = self.compartment_id,
                    sort_order = "ASC"
                )
                results = list_alarms_response.data
                if len(results) > 0:
                    for a in results:
                        if a.lifecycle_state == "ACTIVE":
                            self.alarms.append(a)
                    
            return True
        
    def return_all_alarms(self):
        
        if len(self.alarms) == 0:
        
            return None
        
        else:
            
            return self.alarms
        
    def return_alarm(self, display_name):
        
        for a in self.alarms:
            if a.display_name == display_name:
                return a

# end class GetAlarms


class GetInputOptions:
    '''
    Method parses an argument list for arguments and their respective
    inputs. Input options with data input items minus the pre-options
    inputs must be a mod return value of 0 in order for
    self.options_list_with_input to populate. Your code must supply the
    starting index from where the methods begin this check. If you populate and
    get a length != 0, then the input list from the starting index in the list
    is uneven. The method populate_input_options() handles this. It returns
    True if the mod op returns 0 and also populates its list, or it returns
    False if the mod op is non-zero.
    
    Your calling program logic must handle this condition.

    Pass to this method an argument vector of data inputs to the CLI to
    instiate the data as in:
        my_arg_list = GetInputOptions(sys.argv)

    To extract the argument list with data inputs, do something like th following:
        my_arg_list.populate_input_options(5)
    This will perform a mod calculation, verify the result = 0, and only if equal
    to 0 will it then populate self.options_list_with_input.

    To get an input option's data input, do something like:
    my_input = my_arg_list.return_input_option_data("--DISPLAY-NAME")
    The method will search for the option in the list, and then return the next
    item, which should be the user's input.
    
    To get the value for a particular vale passed in sys.argv, call the method 
    return_input_option_data() and pass to it the option you are searching for,
    such as return_input_option_data("--access"). The method will return the
    next value in the list, which will be the value your code is searching for.

    See Oci-AddExportFsEntry.py for a use case of this class.
    '''
    def __init__(self, my_list):
        self.argument_list = my_list
        self.options_list_with_input = []
        
    def populate_input_options(self, start_position):
        if (len(self.argument_list) - (start_position + 1)) % 2:
            cntr = start_position
            while cntr < len(self.argument_list):
                self.options_list_with_input.append(self.argument_list[cntr].upper())
                self.options_list_with_input.append(self.argument_list[cntr+1])
                cntr += 2
            return True
        else:
            return False
    
    def return_input_option_data(self, my_option):
        cntr = 0
        for item in self.argument_list:
            if item.upper() == my_option.upper():
                return self.argument_list[cntr + 1]
            cntr += 1

        return None # if we get this far, we need to return something to test for

# end class GetInputOptions

class GetNotificationItems:
    '''
    The method populate_notification_lists() returns all objects of type NotificationTopicSummary
    that are not TERMINATED or TERMINATING and stores the data in self.notification_topics
    
    The method return_all_notificaton_topics() returns all objects of type notification_topics
    if present, otherwise it returns None
    
    The method return_notifcation(display_name) returns the specified notification topic if
    found, otherwise it returns None
    '''
    
    def __init__(
        self,
        ons_client,
        compartment_id):
        
        self.compartment_id      = compartment_id
        self.ons_client          = ons_client
        self.notification_topics = []
        
    def populate_notification_lists(self):
        # populates the class
        
        if len(self.notification_topics) != 0:
            return False
        else:
            list_topics_response = self.ons_client.list_topics(
                compartment_id = self.compartment_id,
                sort_order     = "ASC"
            ).data
            
            for i in list_topics_response:
                if i.lifecycle_state == "ACTIVE":
                    self.notification_topics.append(i)
            return True
    
    def return_all_notificaton_topics(self):
        # returns all topics in class
        
        if len(self.notification_topics) != 0:
            return self.notification_topics
        else:
            return None
            
    def return_notification_topic(self, notification_topic):
        # returns the specified notification topic if found within the class
        
        returned_item = None
        for i in self.notification_topics:
            if i.name == notification_topic:
                returned_item = i
                
        return returned_item

# end class GetNotificationItems

def error_trap_resource_found(
    item,
    description
    ):

    if item is not None:
        print(
            "\n\nWARNING! - " + description + "\n\n"
        )
        raise RuntimeWarning("WARNING! Resource already present\n")

# end function error_trap_resource_found()

def copywrite():
    print(
        "\nVerion 2.1d\n" +
        "Copyright 2019 – 2022 Kent Cloud Solutions, Inc.,\n" +
        "David Kent Consulting, Inc., and its subsidiaries. - All rights reserved.\n" +
        "Use of this software is subject to the terms and conditions found in the\n" +
        "file LICENSE.TXT. This file is located in the codebase distribution within the\n" +
        "directory /usr/local/bin/KENT/bin\n"
    )
# end function copywrite()

def create_alarm(
    monitoring_client,
    CreateAlarmDetails,
    alarm_name,
    compartment_id,
    namespace,
    query_string,
    severity,
    notification_item_id,
    message_body,
    message_format,
    repeat_notification_duration
    ):

    create_alarm_details = CreateAlarmDetails(
        display_name = alarm_name,
        compartment_id = compartment_id,
        metric_compartment_id = compartment_id,
        namespace = namespace,
        query = query_string,
        severity = severity,
        destinations = [notification_item_id],
        is_enabled = True,
        body = message_body,
        message_format = message_format,
        repeat_notification_duration = repeat_notification_duration
    )

    # return create_alarm_details

    create_alarm_response = monitoring_client.create_alarm(
        create_alarm_details = create_alarm_details
    ).data

    return create_alarm_response

# end function create_alarm

def error_trap_resource_not_found(
    item,
    description):
    '''
    Function tests the length of the expected resource item, if null, then print the message and exit with a run time error.
    Use in your code to check for cloud resource objects that you expect to find. Do not use with lists.

    Usage: error_trap_resource_not_found(<object to check for> <descriptive message>)
    '''
    if item is None:
        print(
            "\n\nWARNING! - " + description + "\n\n" +
            "Please try again with a correct resource name\n\n"
            )
        raise RuntimeWarning("WARNING! - Resource not found\n")

# end function error_trap_resource_not_found

def get_availability_domains(
    identity_client,
    compartment_id):
    '''
    
    This function retrieves the availability domains for the specified compartment.
    
    '''
    
    results = identity_client.list_availability_domains(
        compartment_id = compartment_id).data
    
    return results

# end function get_availability_domain

def get_protocol(
    value):
    '''
    This function returns the RFC defined protocol in text format based on the
    numeric input as supplied by your code. Options are supported only 
    for ICMP (“1”), TCP (“6”), UDP (“17”), and ICMPv6 (“58”). Use this function
    with code that updates OCI security lists or network security groups from
    CSV input files or the inverse, to creatre CSV exports of existing rules.
    
    Call the function as in:
        get_protocol("6")
    will return the string value "TCP"
    '''
    if value == "1":
        return "ICMP"
    elif value == "6":
        return "TCP"
    elif value == "17":
        return "UDP"
    elif value == "58":
        return "ICMPv6"
    elif value == "all":
        return "ALL"
    else:
        return None
# end function get_protocol()

def get_regions(
    identity_client):

    results = identity_client.list_regions().data

    return results

# end function get_regions()

def get_subscriber_regions(
    identity_client,
    tenancy_id):
    
    # this function gets a list of all regions the tenancy is subscribed to and returns it as a dictionary object.
    # it requires that the identity client be loaded. You must supply the tenancy OCID (root compartment).
    # If using the KENT code class GetParentCompartment(), the value compartment_id of the returned object
    # contains the tenancy OCID
    list_region_subscriptions_response = identity_client.list_region_subscriptions(
        tenancy_id = tenancy_id
    ).data
    
    return list_region_subscriptions_response

# end function get_subscriber_regions

def is_int(my_input):
    '''
    Function returns true if the input value chars in the string are all numbers,
    otherwise it returns false. This function is useful to type check user input
    for int type or string type.
    '''
    for my_char in my_input:
        if my_char.isalpha():
            return False
    return True

# end function is_string

def make_sure_export_file_is_not_zero_bytes(
    file_name):
    
    if os.path.getsize(file_name) == 0:
        print(
            "\n\nWARNING! - Unable to create export file as expected. Please make sure\n" +
            "your input values are correct and inspect any preceeded errors.\n\n" +
            "Please try again with a correct virtual cloud network name.\n\n"
        )
        raise RuntimeError("EXCEPTION! - Unable to create file\n")
# end function make_sure_export_file_is_not_zero_bytes

def read_pub_ssh_keys_from_dir(ssh_key_dir):
    ssh_public_keys = []
    file_list = os.listdir(ssh_key_dir)
    for file_name in file_list:
        if ".pub" in file_name:
            ssh_key_path = os.path.expandvars(os.path.expanduser(ssh_key_dir + "/" + file_name))
            with open(ssh_key_path, mode="r") as file:
                ssh_key = file.read()
            ssh_public_keys.append(ssh_key)
    return ssh_public_keys

def return_availability_domain(
    identity_client,
    compartment_id,
    ad_number):
    '''
    Function returns the availability domain name based on the inout of the
    compartment ID and the availability zone number. A result of None is
    returned if a number outside of 1-3 is entered for ad_number.
    
    Usage:
        my_ad_name = return_availability_domain(
            compartment_id,
            2)
    returns the name of availability domain 2 within compartment_id
    '''
    
    if ad_number > 0 and ad_number <= 3:
        availability_domains = get_availability_domains(
            identity_client,
            compartment_id)
    
        return availability_domains[ad_number - 1].name
    else:
        return None

    # end function return_availability_domain()

def test_free_mem_1gb():
    '''
    The purpose of this function is to test to see if at least 2GB
    is on the free list. If so, we return True, if not, we return
    False. The function requires that platform be imported by
    your code, or loaded by this library.
    '''

    if platform.system() == "Linux":

        with open('/proc/meminfo', 'r') as mem:
            free_memory = 0
            for i in mem:
                sline = i.split()
                if str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                    free_memory += int(sline[1])

        if free_memory < 1024000:
            return False
        else:
            return True
    else:
        # we'll not test for at least 2GB free RAM on non-Linux instances.
        # This may have to be tweaked after we containerize since the platform
        # response may change. In production, we will abort if we are not running
        # on a supported platform.
        return True

# end function test_free_mem_1gb()

def test_free_mem_2gb():
    '''
    The purpose of this function is to test to see if at least 2GB
    is on the free list. If so, we return True, if not, we return
    False. The function requires that platform be imported by
    your code, or loaded by this library.
    '''

    if platform.system() == "Linux":

        with open('/proc/meminfo', 'r') as mem:
            free_memory = 0
            for i in mem:
                sline = i.split()
                if str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                    free_memory += int(sline[1])

        if free_memory < 2048000:
            return False
        else:
            return True
    else:
        # we'll not test for at least 2GB free RAM on non-Linux instances.
        # This may have to be tweaked after we containerize since the platform
        # response may change. In production, we will abort if we are not running
        # on a supported platform.
        return True

# end function test_free_mem_2gb()

def warning_beep(number_of_beeps):
    my_count = 0
    while my_count < int(number_of_beeps):
        print("WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING!")
        print("\a")
        sleep(1)
        my_count += 1

# end function warning_beep()