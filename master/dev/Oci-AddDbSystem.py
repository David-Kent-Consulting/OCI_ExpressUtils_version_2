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

# Required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import return_availability_domain
from lib.general import get_regions
from lib.general import is_int
from lib.general import warning_beep
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.database import create_virtual_db_machine
from lib.database import GetDbNode
from lib.database import GetDbSystem
from lib.subnets import GetPrivateIP
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# Required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.database import DatabaseClient
from oci.database import DatabaseClientCompositeOperations
from oci.core import VirtualNetworkClient

# required OCI decorators
from oci.database.models import CreateDatabaseDetails
from oci.database.models import CreateDbHomeDetails
from oci.database.models import DbSystemOptions
from oci.database.models import LaunchDbSystemDetails

# define DB system properties dictionary object
virtual_db_system_properties = {
    "availability_domain"             : "",
    "admin_password"                  : "",
    "database_edition"                : "",
    "display_name"                    : "",
    "db_name"                         : "",
    "db_workload"                     : "",
    "pdb_name"                        : "",
    "storage_management"              : "",
    "hostname"                        : "",
    "initial_data_storage_size_in_gb" : "",
    "license_model"                   : "",
    "node_count"                      : "",
    "shape"                           : "",
    "cpu_count"                       : "",
    "ssh_public_keys"                 : "",
    "time_zone"                       : ""
}

copywrite()
sleep(2)
if not len(sys.argv) > 22:
    print(
        "\n\nOci-AddDbSystem.py : Usage\n\n" +
        "Oci-AddDbSystem.py [parent compartment] [child compartment] [virtual cloud network]\n" +
        "\t[subnetwork] [availability domain number] [Database Container name] [DB name] [PDB name]\n" +
        "\t[workload (OLTP/DSS)] [storage type (ASM/LVM)] [service node name] [storage size] [node count]\n" +
        "\t[SSH public key file] [time zone] [password for DB System] [database edition] [database version]\n" +
        "\t[shape] [CPU Count] [license model (LICENSE_INCLUDED/BRING_YOUR_OWN_LICENSE)] [region]\n" +
        "[private ip address (optional)]\n" +
        "CAVEAT: Once a CPU architecture is selected (AMD/INTEL), it cannot be modified. We recommend AMD\n" +
        "over INTEL due to its increased processor licensing flexibility.\n\n"
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeWarning("INCORRECT USAGE")


parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
virtual_network_name                = sys.argv[3]
subnet_name                         = sys.argv[4]
region                              = sys.argv[22]

private_ip                          = ""

if len(sys.argv) == 24:
    private_ip                      =sys.argv[23]
else:
    print ("\n\nDefault assignment of random IP will be used.\n\n")

if not is_int(sys.argv[5]):
    warning_beep(1)
    raise RuntimeWarning("Availability domain number must be a number between 1 and 3")
availability_domain_number          = int(sys.argv[5])
if availability_domain_number not in [1,2,3]:
    warning_beep(1)
    raise RuntimeWarning("Availability domain number must be a number between 1 and 3")

virtual_db_system_properties["db_conatiner_name"]       = sys.argv[6]
virtual_db_system_properties["display_name"]            = sys.argv[6]
virtual_db_system_properties["db_name"]                 = sys.argv[7]
virtual_db_system_properties["pdb_name"]                = sys.argv[8]

virtual_db_system_properties["db_workload"]             = sys.argv[9]
if virtual_db_system_properties["db_workload"] not in ["OLTP", "DSS"]: # OLTP for transactional DB, DSS for warehouse DB
    warning_beep(1)
    raise RuntimeWarning("Database workload type must be either OLTP or DSS")

virtual_db_system_properties["storage_management"]      = sys.argv[10]
if virtual_db_system_properties["storage_management"] not in ["ASM", "LVM"]: # ASM for grid control, LVM for logical volumes
    warning_beep(1)
    raise RuntimeWarning("Storage type must be ASM or LVM")

virtual_db_system_properties["hostname"]                = sys.argv[11]

if not is_int(sys.argv[12]):
    warning_beep(1)
    raise RuntimeWarning("Storage size must be a number")
virtual_db_system_properties["initial_data_storage_size_in_gb"] = int(sys.argv[12])
if virtual_db_system_properties["initial_data_storage_size_in_gb"] not in [256, 512, 1024, 2048, 4096, 6144, 8192, 10240, 12288, 14336, 16384, 18432, 20480, 22528, 24576, 26624, 28672, 30720, 32768]:
    warning_beep(1)
    print(
        "Storage must be a number in the following range:\n" +
        "\t256, 512, 1024, 2048, 4096, 6144, 8192, 10240, 12288,\n" +
        "\t14336, 16384, 18432, 20480, 22528, 24576, 26624, 28672\n" +
        "\t30720, 32768\n"+
        "Please try again with a correct value.\n\n"
    )
    raise RuntimeWarning("Incorrect Value")

if not is_int(sys.argv[13]) or sys.argv[13] not in ["1", "2"]:
    warning_beep(1)
    raise RuntimeWarning("Node count must be a number between 1 and 2")
virtual_db_system_properties["node_count"]              = int(sys.argv[13])

if not os.path.exists(sys.argv[14]):
    warning_beep(1)
    raise RuntimeWarning("SSH public keyfile not found")
ssh_key_path                          = os.path.expandvars(os.path.expanduser(sys.argv[14]))
with open(ssh_key_path, mode='r') as file:
    ssh_key = file.read()
virtual_db_system_properties["ssh_public_keys"]         = ssh_key

virtual_db_system_properties["time_zone"]               = sys.argv[15]

virtual_db_system_properties["admin_password"]          = sys.argv[16]
if sys.argv[17] not in [
    "STANDARD_EDITION",
    "ENTERPRISE_EDITION",
    "ENTERPRISE_EDITION_HIGH_PERFORMANCE",
    "ENTERPRISE_EDITION_EXTREME_PERFORMANCE"]:
    RuntimeWarning("INVALID VALUE FOR DATABASE EDITION!")

virtual_db_system_properties["database_edition"]        = sys.argv[17]
virtual_db_system_properties["db_version"]              = sys.argv[18]

db_system_shapes = [
    "VM.Standard2.1",
    "VM.Standard2.2",
    "VM.Standard2.4",
    "VM.Standard2.8",
    "VM.Standard2.16",
    "VM.Standard2.24",
    "VM.Standard.E4.Flex"
]

if sys.argv[19] not in db_system_shapes:
    raise RuntimeWarning("\n\nINVALID SHAPE. Please try again.\n\n")
virtual_db_system_properties["shape"]                   = sys.argv[19]

virtual_db_system_properties["cpu_count"]               = sys.argv[20]
virtual_db_system_properties["license_model"]           = sys.argv[21]


# instiate the environment and validate that the specified region exists
print("\n\nFetching and verifying tenant resource data to DB System creation values. Please wait......\n")
config = from_file() # gets ~./.oci/config and reads to the object
identity_client = IdentityClient(config)
regions = get_regions(identity_client)
correct_region = False
for rg in regions:
    if rg.name == region:
        correct_region = True
if not correct_region:
    warning_beep(1)
    print("\n\nWARNING! - Region {} does not exist in OCI. Please try again with a correct region.\n\n".format(
        region
    ))
    raise RuntimeWarning("WARNING! INVALID REGION")

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
database_client = DatabaseClient(config)
network_client  = VirtualNetworkClient(config)

# get parent compartment data
parent_compartments = GetParentCompartments(parent_compartment_name, config, identity_client)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Unable to find parent compartment " + parent_compartment_name + " within tenancy " + config["tenancy"]
)

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Unable to find child compartment " + child_compartment_name + " in parent compartment " + parent_compartment_name
)

# get virtual cloud network data
virtual_networks = GetVirtualCloudNetworks(
    network_client,
    child_compartment.id,
    virtual_network_name
)
virtual_networks.populate_virtual_cloud_networks()
virtual_network = virtual_networks.return_virtual_cloud_network()
error_trap_resource_not_found(
    virtual_network,
    "Virtual network " + virtual_network_name + " not found within compartment " + child_compartment_name + " within region " + region
)

# get subnet data
subnets = GetSubnet(
    network_client,
    child_compartment.id,
    virtual_network.id,
    subnet_name
)
subnets.populate_subnets()
subnet = subnets.return_subnet()
error_trap_resource_not_found(
    subnet,
    "Subnet " + subnet_name + " not found within virtual cloud network " + virtual_network_name
)

# if we have a potentially valid ipV4 address, say 10.0.0.1
if len(private_ip) > 7:
    # Verify the selected IP address is not in use
    private_ip_addresses = GetPrivateIP(
        network_client,
        subnet.id
    )

    private_ip_addresses.populate_ip_addresses()
    private_ip_addr = private_ip_addresses.return_ip_by_address(private_ip)
    error_trap_resource_found(
        private_ip_addr,
        "Private IP address " + private_ip + " already assigned to subnetwork '" + subnet_name + "'"
    )

# get DB system data and return error if the DB System is found
db_systems = GetDbSystem(
    database_client,
    child_compartment.id
)
db_systems.populate_db_systems()
db_system = db_systems.return_db_system_from_display_name(virtual_db_system_properties["db_conatiner_name"])
error_trap_resource_found(
    db_system,
    "Database system " + virtual_db_system_properties["db_conatiner_name"] + " already present within compartment " + child_compartment_name + " within region " + region
)

'''
We have to check for duplicate node names. In order to do this, we must walk down each DB system in the class db_systems.db_systems
and call GetDbNode, inspect the node names, and exit if a duplicate is found. This is because the API links DB nodes to db_system_id.
'''
for dbs in db_systems.db_systems:
    tmp_db_nodes = GetDbNode(
        database_client,
        child_compartment.id,
        dbs.id
    )
    tmp_db_nodes.populate_db_service_nodes()
    for dbn in tmp_db_nodes.db_nodes:
        if dbn.hostname == virtual_db_system_properties["hostname"]:
            print("\n\nWARNING! Service node name {} is already assigned to DB System {}.\n".format(
                virtual_db_system_properties["hostname"],
                dbs.display_name
            ))
            print("Duplicate host names are not permitted.\n\n")
            raise RuntimeWarning("WARNING! Duplicate service node names not permitted.")
    tmp_db_nodes = None


# Get the availability domain name
virtual_db_system_properties["availability_domain"] = return_availability_domain(
    identity_client,
    child_compartment.id,
    availability_domain_number
)

# proceed to create the DB System
print("Submitting the request to create DB system {} within compartment {} in region {}\n".format(
    virtual_db_system_properties["db_conatiner_name"],
    child_compartment_name,
    region
))
virtual_db_machine_launch_response = create_virtual_db_machine(
    database_client,
    CreateDatabaseDetails,
    CreateDbHomeDetails,
    DbSystemOptions,
    LaunchDbSystemDetails,
    child_compartment.id,
    subnet.id,private_ip,
    virtual_db_system_properties
)
if virtual_db_machine_launch_response.data.lifecycle_state == "PROVISIONING":
    print("Request to create DB System {} successful. It will take between 20-60 minutes for this task to complete.\n".format(
        virtual_db_system_properties["display_name"]
    ))
    print("Please review the results below.\n")
    sleep(5)
    print(virtual_db_machine_launch_response.data)
else:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")


