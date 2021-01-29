import os
from oci.database import DatabaseClient
from oci.database.models import CreateDatabaseDetails
from oci.database.models import CreateDbHomeDetails
from oci.database.models import DbSystemOptions
from oci.database.models import LaunchDbSystemDetails

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
    virtual_db_system_properties
    ):
    
    launch_db_system_details = LaunchDbSystemDetails(
        availability_domain = virtual_db_system_properties["availability_domain"],
        compartment_id = compartment_id,
        database_edition = virtual_db_system_properties["database_edition"],
        db_home = CreateDbHomeDetails(
            db_version = virtual_db_system_properties["db_version"],
            display_name = virtual_db_system_properties["db_name"],
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
        shape = virtual_db_system_properties["shape"],
        ssh_public_keys = [virtual_db_system_properties["ssh_public_keys"]],
        subnet_id = subnet_id,
        node_count = virtual_db_system_properties["node_count"]
    )
    
    virtual_db_machine_launch_response = database_client.launch_db_system(
        launch_db_system_details
    )
    
    return virtual_db_machine_launch_response

# end function create_virtual_db_machine()