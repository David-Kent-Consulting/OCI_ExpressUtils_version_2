#!/usr/bin/python3
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
# required system modules
import os.path
import sys
from tabulate import tabulate
from time import sleep

# required DKC modules
from lib.general import copywrite
from lib.general import error_trap_resource_found
from lib.general import error_trap_resource_not_found
from lib.general import get_regions
from lib.compute import GetImages
from lib.container import create_cluster
from lib.compartments import GetParentCompartments
from lib.compartments import GetChildCompartments
from lib.container import create_cluster
from lib.container import GetCluster
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient
from oci.container_engine import ContainerEngineClient


if len(sys.argv) < 5 or len(sys.argv) > 6: # ARGS PLUS COMMAND
    print(
        "\n\nOci-GetKbCluster.py : Usage\n" +
        "Oci-GetKbCluster.py [parent_compartment] [child_compartment] [cluster name] [region] [optional argument]\n\n"
        "Use case example 1 list all Kubernetes clusters within the specified compartment:\n" +
        "\tOci-GetKbCluster.py admin_comp dbs_comp list_all_clusters 'us-ashburn-1'\n" +
        "Use case example 2 lists the specified Kubernetes cluster within the specified compartment and region:\n" +
        "\tOci-GetKbCluster.py admin_comp dbs_comp kentkbct01 'us-ashburn-1'\n\n" +
        "Please see the online documentation at the David Kent Consulting GitHub repository for more information.\n\n"
    )
    raise RuntimeError("Invalid number of arguments provided to the script. Consult the script header for required arguments")


# Instiate all vars and classes
parent_compartment_name             = sys.argv[1]
child_compartment_name              = sys.argv[2]
cluster_name                        = sys.argv[3]
region                              = sys.argv[4]
if len(sys.argv) == 6:
    option = sys.argv[5].upper()
else:
    option = None # required for logic to work
if option != "--JSON":
    copywrite()
    sleep(2)
    print("\n\nFetching and validating tenancy resources......\n")

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


# run through the logic
if sys.argv[3].upper() == "LIST_ALL_CLUSTERS":

    header = [
        "COMPARTMENT",
        "CLUSTER",
        "VERSION",
        "LIFECYCLE STATE",
        region
    ]
    data_rows = []
    for kbc in clusters.return_all_clusters():
        data_row = [
            child_compartment_name,
            kbc.name,
            kbc.kubernetes_version,
            region
        ]
        data_rows.append(data_row)
    print(tabulate(data_rows, headers = header, tablefmt = "grid"))

else:

    error_trap_resource_not_found(
        cluster,
        "Cluster " + cluster_name + " not found in compartment " + child_compartment_name +"\n\n"
    )

    if len(sys.argv) == 5:
        
        header = [
            "COMPARTMENT",
            "CLUSTER",
            "VERSION",
            "KUBERNETES DASHBOARD STATE",
            "PODS CIDR",
            "SERVICES CIDR",
            "LIFECYCLE STATE",
            "REGION"
        ]
        data_rows = [[
            child_compartment_name,
            cluster.name,
            cluster.kubernetes_version,
            cluster.options.add_ons.is_kubernetes_dashboard_enabled,
            cluster.options.kubernetes_network_config.pods_cidr,
            cluster.options.kubernetes_network_config.services_cidr,
            cluster.lifecycle_state,
            region
        ]]
        print(tabulate(data_rows, headers = header, tablefmt = "simple"))
        print("\nCLUSTER ID :\t" + cluster.id + "\n\n")
        
    elif option == "--OCID":
        print(cluster.id)
    elif option == "--NAME":
        print(cluster.name)
    elif option == "--AVAILABLE-UPGRADES":
        print(cluster.available_kubernetes_upgrades)
    elif option == "--LIFECYCLE-STATE":
         print(cluster.lifecycle_state)
    elif option == "--METADATA":
        print(cluster.metadata)
    elif option == "--NETWORK-CONFIG":
        print(cluster.options.kubernetes_network_config)
    elif option == "--JSON":
        print(cluster)
    else:
        print(
            "\n\nINVALID OPTION! - Valid options are:\n" +
            "\t--ocid\t\t\tPrint the OCID of the cluster\n" +
            "\t--name\t\t\tPrint the name of the cluster\n" +
            "\t--available-upgrades\tPrints any upgrades that may be available for the cluster\n" +
            "\t--lifecycle-state\tPrints the cluster's lifecycle status\n" +
            "\t--metadata\t\tPrints the cluster metadata information\n" +
            "\t--network-config\tPrints the cluster's network configuration\n" +
            "\t--json\t\t\tPrints resource data in JSON format and surpresses other output\n\n" +
            "Please try again with a correct option.\n\n"
        )
        raise RuntimeWarning("WARNING! Invalid option")


