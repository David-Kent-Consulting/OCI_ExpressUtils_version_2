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

import os
from urllib import response
from oci.database import DatabaseClient
from oci.database.models import CreateDatabaseDetails
from oci.database.models import CreateDbHomeDetails
from oci.database.models import DbSystemOptions
from oci.database.models import LaunchDbSystemDetails


class GetDatabase:
    '''
    This class gets and returns data for databases. You must supply compartment_id
    and db_home_id.
    '''
    
    def __init__(
        self,
        database_client,
        compartment_id,
        db_home_id):
        
        self.database_client = database_client
        self.compartment_id = compartment_id
        self.db_home_id = db_home_id
        self.databases = []
    
    def populate_databases(self):

        if len(self.databases) != 0:
            return None
        else:
            results = self.database_client.list_databases(
                compartment_id = self.compartment_id,
                db_home_id = self.db_home_id
            ).data
            for db in results:
                if db.lifecycle_state != "TERMINATED" and db.lifecycle_state != "TERMINATING":
                    self.databases.append(db)

    def return_all_databases(self):

        if len(self.databases) == 0:
            return None
        else:
            return self.databases

    def return_database_display_name(self, database_name):

        if len(self.databases) == 0:
            return None
        else:
            for db in self.databases:
                if db.db_name == database_name:
                    return db
    
    def __str__(self):
        
        return "GetDatabase class setup to operate within compartment " + self.compartment_id
    
# end class GetDatabase
class GetDbHome:
    '''
    This class collects data and returns data for DB homes based on the called methods.
    You must supply the compartment_id and the db_system_id when instiating the class
    '''
    
    def __init__(
        self,
        database_client,
        comparetment_id,
        db_system_id):
        
        self.database_client = database_client
        self.comparetment_id = comparetment_id
        self.db_system_id = db_system_id
        self.db_homes = []
    
    def populate_db_homes(self):
        
        if len(self.db_homes) != 0:
            return None
        else:
            results = self.database_client.list_db_homes(
                compartment_id = self.comparetment_id,
                db_system_id = self.db_system_id
            ).data
            for dbh in results:
                if dbh.lifecycle_state != "TERMINATED" and dbh.lifecycle_state != "TERMINATING":
                    self.db_homes.append(dbh)
    
    def return_all_db_homes(self):
        
        if len(self.db_homes) == 0:
            return None
        else:
            return self.db_homes
    
    def return_db_dome_display_name(self, db_home_name):
        
        if len(self.db_homes) == 0:
            return None
        else:
            for dbh in self.db_homes:
                if dbh.display_name == db_home_name:
                    return dbh
    
    def __str__(self):
        
        return "Class setup to perform tasks in compartment " + self.comparetment_id

# end class GetDbHome

class GetDbNode:
    '''
    This class and methods store data about database service nodes and return data based
    on the called method. There is a document defect at
       https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/database/client/oci.database.DatabaseClient.html#oci.database.DatabaseClient.list_db_nodes
    The db_system_id or vm_cluster_id is required.
    '''
    
    def __init__(
        self,
        database_client,
        compartment_id,
        db_system_id):
        
        self.database_client = database_client
        self.compartment_id = compartment_id
        self.db_system_id = db_system_id
        self.db_nodes = []
    
    def populate_db_service_nodes(self):

        if len(self.db_nodes) != 0:
            return None
        else:
            results = self.database_client.list_db_nodes(
                compartment_id = self.compartment_id,
                db_system_id = self.db_system_id,
                sort_order = "ASC"
            ).data
        for dbn in results:
            if dbn.lifecycle_state != "TERMINATED" and dbn.lifecycle_state != "TERMINATING":
                self.db_nodes.append(dbn)
    
    def return_all_db_service_nodes(self):
        
        if len(self.db_nodes) == 0:
            return None
        else:
            return self.db_nodes

    def return_db_service_from_db_system_id(self, db_system_id):

        if len(self.db_nodes) == 0:
            return None
        else:
            for dbn in self.db_nodes:
                if dbn.db_system_id == db_system_id:
                    return dbn
    
    def return_db_service_node_display_name(self, db_node_name):
        
        if len(self.db_nodes) == 0:
            return None
        else:
            for dbn in self.db_nodes:
                if dbn.hostname == db_node_name:
                    return dbn
    
    def __str__(self):
        
        return "Class setup to perform tasks in compartment " + self.compartment_id

# end class GetDbNode

class GetDbShapes:
    '''
    
    
    '''

    def __init__(
        self,
        database_client,
        compartment_id):

        self.database_client = database_client
        self.compartment_id  = compartment_id
        self.db_system_shapes = []

    

class GetDbSystem:
    '''
    This class and associated methods collect data from OCI regarding DB systems and return
    responses based on inputs.
    
    See https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/database/client/oci.database.DatabaseClient.html#oci.database.DatabaseClient.list_db_systems 
    for reference material. Instiate with database_client and compartment_id, then use the
    methods to both populate and extract data.
    '''
    
    def __init__(
        self,
        database_client,
        compartment_id):
        
        self.database_client = database_client
        self.compartment_id = compartment_id
        self.db_systems = []

    def populate_db_systems(self):
        if len(self.db_systems) != 0:
            return None
        
        results = self.database_client.list_db_systems(
            compartment_id = self.compartment_id
        ).data
        
        for dbs in results:
            if dbs.lifecycle_state != "TERMINATED" and dbs.lifecycle_state != "TERMINATING":
                self.db_systems.append(dbs)
    
    def return_all_db_systems(self):
        
        if len(self.db_systems) == 0:
            return None
        else:
            return self.db_systems
    
    def return_db_system_from_display_name(self, dbsystem_name):
        
        if len(self.db_systems) == 0:
            return None
        else:
            for dbs in self.db_systems:
                if dbs.display_name == dbsystem_name:
                    return dbs
    
    def __str__(self):
        return "Class setup to perform DB system queries from compartment " + self.compartment_id

# end class GetDbSystem


def create_virtual_db_machine(
    database_client,
    CreateDatabaseDetails,
    CreateDbHomeDetails,
    DbSystemOptions,
    LaunchDbSystemDetails,
    compartment_id,
    subnet_id,
    private_ip,
    virtual_db_system_properties
    ):
    
    launch_db_system_details = LaunchDbSystemDetails(
        availability_domain = virtual_db_system_properties["availability_domain"],
        compartment_id = compartment_id,
        cpu_core_count = int(virtual_db_system_properties["cpu_count"]),
        database_edition = virtual_db_system_properties["database_edition"],
        db_home = CreateDbHomeDetails(
            db_version = virtual_db_system_properties["db_version"],
            display_name = virtual_db_system_properties["db_conatiner_name"],
            database = CreateDatabaseDetails(
                admin_password = virtual_db_system_properties["admin_password"],
                db_name = virtual_db_system_properties["db_name"],
                db_workload = virtual_db_system_properties["db_workload"],
                pdb_name = virtual_db_system_properties["pdb_name"]
            )
        ),
        db_system_options = DbSystemOptions(
            storage_management = virtual_db_system_properties["storage_management"]
        ),
        display_name = virtual_db_system_properties["display_name"],
        hostname = virtual_db_system_properties["hostname"],
        initial_data_storage_size_in_gb = virtual_db_system_properties["initial_data_storage_size_in_gb"],
        license_model = virtual_db_system_properties["license_model"],
        shape = virtual_db_system_properties["shape"],
        ssh_public_keys = [virtual_db_system_properties["ssh_public_keys"]],
        subnet_id = subnet_id,
        private_ip = private_ip,
        node_count = virtual_db_system_properties["node_count"],
        time_zone = virtual_db_system_properties["time_zone"]
    )
    
#     return launch_db_system_details
    
    virtual_db_machine_launch_response = database_client.launch_db_system(
        launch_db_system_details
    )
    
    return virtual_db_machine_launch_response

# end function create_virtual_db_machine()

def increase_db_system_storage(
    database_composite_client,
    UpdateDbSystemDetails,
    db_system,
    data_storage_size_in_gbs):
    '''
    This function will increase the storage of a DB System. There are a number of
    critical pre-requisits that must be met prior to applying this change. A
    failure to miss any one of these pre-reqs may result in corruption of the
    DB System. 
    
    WARNING! The database running on the DB System must be in an OPEN state
    prior to calling this function. It is not possible for us to check this
    with the OCI APIs. The recommended practice for applying the change change
    in your code should be to always prompt and warn the user prior to calling
    this function.
    
    You must pass the full RESTFUL objects for db_system
    along with a valid value to which to increase storage to. The logic will check 
    each of these resources to ensure a state of AVAILABLE. Unlike other functions,
    this function will enforce correct pre-reqs prior to applying the change.
    We return False if any of these pre-req checks fail.
    '''
    
    if db_system.lifecycle_state == "AVAILABLE":
   
        update_db_system_details = UpdateDbSystemDetails(
            data_storage_size_in_gbs = data_storage_size_in_gbs
        )

        increase_db_system_storage_response = database_composite_client.update_db_system_and_wait_for_state(
            db_system_id = db_system.id,
            update_db_system_details = update_db_system_details,
            wait_for_states = ["AVAILABLE", "TERMINATING", "TERMINATED", "FAILED", "NEEDS_ATTENTION", "UNKNOWN_ENUM_VALUE"]
        )
        return increase_db_system_storage_response
        
    else:
        return False

# end function increase_db_system_storage()


def start_stop_db_node(
    database_composite_client,
    db_node_id,
    action
    ):
    '''
    This function starts or stops a DB system's service node. Your code must provide
    db_node_id, which can ge obtained by calling GetDbSystem, and then by
    calling DbNode, both of which are part of the DKC codebase.
    
    The use case below starts the DB system service node:
    
        start_stop_db_node(
            database_composite_client,
            db_node_id,
            "START")
    
    The function returns the results of the resource action.
    
    Allowable actions are: STOP, START, SOFTRESET, RESET. RESET is an ungraceful
    action. All other actions are graceful.
    
    Your code must meet all pre-requisits prior to calling this function.
    Your code must check the results for success or failure upon completion.
    '''
    
    db_node_action_results = database_composite_client.db_node_action_and_wait_for_state(
        db_node_id = db_node_id,
        action = action,
        wait_for_states = ["AVAILABLE", "STOPPED", "STOPPING", "TERMINATING", "TERMINATED", "FAILED", "UNKNOWN_ENUM_VALUE"]
    )
    
    return db_node_action_results

# end function start_stop_db_node

def terminate_db_system(
    database_composite_client,
    db_system_id):
    '''
    This function deletes a DB System. It is your responsibility to prompt and
    warn the user in your code prior to calling this function.
    '''
    
    terminate_db_system_request_results = database_composite_client.terminate_db_system_and_wait_for_work_request(
        db_system_id = db_system_id
    )
    
    return terminate_db_system_request_results

# end function terminate_db_system()

def update_db_system_license_model(
    database_composite_client,
    UpdateDbSystemDetails,
    db_system,
    license_model):
    '''
    This function will modify the license model of a DB System. There are a number of
    critical pre-requisits that must be met prior to applying this change. A
    failure to miss any one of these pre-reqs may result in corruption of the
    DB System. 
    
    WARNING! The database running on the DB System must be in an OPEN state
    prior to calling this function. It is not possible for us to check this
    with the OCI APIs. The recommended practice for applying the change change
    in your code should be to always prompt and warn the user prior to calling
    this function.
    
    You must pass the full RESTFUL objects for db_system
    along with a valid license model value. The logic will check each of these resources to
    ensure a state of AVAILABLE. Unlike other functions, this function will enforce
    correct pre-reqs prior to applying the change. We return False if any of
    these pre-req checks fail.
    '''
    
    if db_system.lifecycle_state == "AVAILABLE":
   
        update_db_system_details = UpdateDbSystemDetails(
            license_model = license_model
        )
        db_system_license_model_change_action = database_composite_client.update_db_system_and_wait_for_state(
            db_system_id = db_system.id,
            update_db_system_details = update_db_system_details,
            wait_for_states = ["AVAILABLE", "TERMINATING", "TERMINATED", "FAILED", "NEEDS_ATTENTION", "UNKNOWN_ENUM_VALUE"]
        )
        return db_system_license_model_change_action
        
    else:
        return False

# end function update_db_system_license_model()

def update_db_system_shape(
    database_composite_client,
    UpdateDbSystemDetails,
    db_system,
    shape):
    '''
    This function will modify the shape of a DB System. There are a number of
    critical pre-requisits that must be met prior to applying a shape change. A
    failure to miss any one of these pre-reqs may result in corruption of the
    DB System. 
    
    WARNING! The database running on the DB System must be in an OPEN state
    prior to calling this function. It is not possible for us to check this
    with the OCI APIs. The recommended practice for applying the shape change
    in your code should be to always prompt and warn the user prior to calling
    this function.
    
    You must pass the full RESTFUL objects for db_system
    along with a valid shape. The logic will check each of these resources to
    ensure a state of AVAILABLE. Unlike other functions, this function will enforce
    correct pre-reqs prior to applying the shape change. We return False if any of
    these pre-req checks fail.
    '''
    
    if db_system.lifecycle_state == "AVAILABLE":
   
        update_db_system_details = UpdateDbSystemDetails(
            shape = shape
        )
        
        db_system_shape_change_action = database_composite_client.update_db_system_and_wait_for_state(
            db_system_id = db_system.id,
            update_db_system_details = update_db_system_details,
            wait_for_states = ["AVAILABLE", "TERMINATING", "TERMINATED", "FAILED", "NEEDS_ATTENTION", "UNKNOWN_ENUM_VALUE"]
        )
        return db_system_shape_change_action
        
    else:
        return False

# end function update_db_system_shape()

def update_db_system_ssh_keys(
    database_composite_client,
    UpdateDbSystemDetails,
    db_system,
    ssh_public_keys):
    '''
    This function will modify the license model of a DB System. There are a number of
    critical pre-requisits that must be met prior to applying this change. A
    failure to miss any one of these pre-reqs may result in corruption of the
    DB System. 
    
    WARNING! The database running on the DB System must be in an OPEN state
    prior to calling this function. It is not possible for us to check this
    with the OCI APIs. The recommended practice for applying the change change
    in your code should be to always prompt and warn the user prior to calling
    this function.
    
    You must pass the full RESTFUL objects for db_system
    along with a valid license model value. The logic will check each of these resources to
    ensure a state of AVAILABLE. Unlike other functions, this function will enforce
    correct pre-reqs prior to applying the change. We return False if any of
    these pre-req checks fail.
    '''
    
    if db_system.lifecycle_state == "AVAILABLE":
   
        update_db_system_details = UpdateDbSystemDetails(
            ssh_public_keys = ssh_public_keys
        )

        # return update_db_system_details
        
        update_db_system_details_response = database_composite_client.update_db_system_and_wait_for_state(
            db_system_id = db_system.id,
            update_db_system_details = update_db_system_details,
            wait_for_states = ["AVAILABLE", "TERMINATING", "TERMINATED", "FAILED", "NEEDS_ATTENTION", "UNKNOWN_ENUM_VALUE"]
        )
        return update_db_system_details_response
        
    else:
        return False

# end function update_db_system_ssh_keys()
