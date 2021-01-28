#!/Users/henrywojteczko/bin/python3
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

# required built-in modules
import os.path
import sys
from time import sleep

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations

# required DKC modules
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.general import warning_beep
from lib.compute import GetImages
from lib.container import delete_cluster
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.container import create_cluster
from lib.container import GetCluster
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks




if len(sys.argv) < 5 or len(sys.argv) > 6: # ARGS PLUS COMMAND
    print(
        "\n\nOci-DeleteKbCluster.py : Usage\n" +
        "Oci-DeleteKbCluster.py [parent_compartment] [child_compartment] [cluster name] [region] [optional argument]\n\n"
    )
    raise RuntimeError("WARNING! - Usage error")


# Instiate all vars and classes
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
cluster_name                        = sys.argv[3]
region                              = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None # required for logic to work

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
network_client = VirtualNetworkClient(config)
compute_client = ComputeClient(config)
container_client = ContainerEngineClient(config)
container_composite_client = ContainerEngineClientCompositeOperations(container_client)


# get parent compartment data
parent_compartments = GetParentCompartments(
    parent_compartment_name,
    config,
    identity_client
)
parent_compartments.populate_compartments()
parent_compartment = parent_compartments.return_parent_compartment()
error_trap_resource_not_found(
    parent_compartment,
    "Parent compartment " + parent_compartment_name + " not found in tenancy " + config["tenancy"]
)

# get child compartment data
child_compartments = GetChildCompartments(
    parent_compartment.id,
    child_compartment_name,
    identity_client
)
child_compartments.populate_compartments()
child_compartment = child_compartments.return_child_compartment()
error_trap_resource_not_found(
    child_compartment,
    "Child compartment " + child_compartment_name + " not found in parent compartment " + parent_compartment_name
)

# get cluster data, abort if cluster already present
clusters = GetCluster(
    container_client,
    cluster_name,
    child_compartment.id
)
clusters.populate_cluster()
cluster = clusters.return_cluster()
error_trap_resource_not_found(
    cluster,
    "Cluster " + cluster_name + " not found in compartment " + child_compartment_name +"\n\n"
)

# run through the logic
results = None
if len(sys.argv) == 5:
    warning_beep(6)
    print("Enter YES to proceed with deleting cluster {} or any other key to abort".format(cluster_name))
    if "YES" == input():
        results = delete_cluster(
            container_client,
            cluster.id
        )
    else:
        print("Delete request aborted.\n")
        exit(0)
elif option != "--FORCE":
    print(
        "\n\nWARNING! The only valid option is --force. Please try again.\n\n"
    )
    raise RuntimeWarning("INVALID OPTION")

results = delete_cluster(
    container_client,
    cluster.id
)

if results is not None:
    sleep(60)
    print("\n\nCluster {} delete request initiated from compartment {} within region {}\n".format(
        cluster_name,
        child_compartment_name,
        region
    ))
    print("This delete operation could take up to 20 minutes to complete.\n\n")
else:
    raise RuntimeError("EXCEPTION! UNKNOWN ERROR")

