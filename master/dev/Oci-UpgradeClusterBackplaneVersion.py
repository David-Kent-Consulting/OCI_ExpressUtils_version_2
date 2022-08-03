#!/usr/bin/python3
# Modify the above entry to point to the client's python3 virtual environment prior to execution

'''
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
'''

# required bsystem modules
import os.path
import sys
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
from lib.container import upgrade_kubernetes_backplane
from lib.general import copywrite
from lib.general import warning_beep
from lib.subnets import GetSubnet
from lib.vcns import GetVirtualCloudNetworks

# required OCI modules
from oci.config import from_file
from oci.identity import IdentityClient
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient
from oci.container_engine import ContainerEngineClient
from oci.container_engine import ContainerEngineClientCompositeOperations

# required OCI models
from oci.container_engine.models import AddOnOptions
from oci.container_engine.models import UpdateClusterDetails

copywrite()
sleep(2)
if len(sys.argv) < 6 or len(sys.argv) > 7:
    print(
        "\n\nOci-UpgradeClusterBackplaneVersion.py : Usage\n" +
        "Oci-UpgradeClusterBackplaneVersion.py [parent_compartment] [child_compartment] [cluster_name] [kubernetes version] [region] [optional --force]\n" +
        "Use case example:\n\n" +
        "\tOci-UpgradeClusterBackplaneVersion.py admin_comp tst_comp KENTKBCT01 'v1.21.5' us-ashburn-1' --force\n\n" +
        "Remove the --force option to be prompted prior to applying the upgrade.\n\n"
    )
    raise RuntimeWarning("INVALID USAGE!\n")

parent_compartment_name         = sys.argv[1]
child_compartment_name          = sys.argv[2]
cluster_name                    = sys.argv[3]
kb_version                      = sys.argv[4]
region                          = sys.argv[5]

if len(sys.argv) == 7:
    if sys.argv[6].upper() == "--FORCE":
        option = sys.argv[6].upper()
    else:
        raise RuntimeWarning("WARNING! The option may only be --force. Please try again")
else:
    option = None

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

# build classes & methods

config["region"] = region # Must set the cloud region
identity_client = IdentityClient(config) # builds the identity client method, required to manage compartments
container_client = ContainerEngineClient(config)

print("\n\nGetting tenancy resource data from OCI......\n")
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

# get cluster data, abort if cluster not present
clusters = GetCluster(
    container_client,
    cluster_name,
    child_compartment.id
)
clusters.populate_cluster()
cluster = clusters.return_cluster()
error_trap_resource_not_found(
    cluster,
    "Cluster " + cluster_name + " not found in child compartment " + child_compartment_name + " within region " + region
)

# check to see if version to push to is in cluster.available_kubernetes_upgrades

upgrade_version_ok = False
for k8sv in cluster.available_kubernetes_upgrades:
    if k8sv == kb_version:
        upgrade_version_ok = True

if not upgrade_version_ok:
    print(
        "\n\nSelected version of Kubernetes backplane version is not available for this backplane version.\n" +
        "Available versions are listed below:\n")
    for k8sv in cluster.available_kubernetes_upgrades:
        print("\t" + k8sv + "\n")
    raise RuntimeError("INVALID KUBERNETES VERSION\n")

# Make sure the cluster lifecycle state is AVAILABLE
if cluster.lifecycle_state != "ACTIVE":
    if cluster.lifecycle_state == "UPDATING":
        print("\nKubernetes cluster {} is currently upgrading.\n".format(
            cluster_name))
    else:
        warning_beep(2)
        print("\nKubernetes cluster {} not in a valid state. Please check the health of the cluster and try again.\n")
    
    raise RuntimeError("INVALID CLUSTER LIFECYCLE STATE\n")

if option != "--FORCE":
    warning_beep(6)
    print("Enter YES to proceed with upgrade of cluster {} in child compartment {} within region {} from version {} to version {}\n".format(
        cluster_name,
        child_compartment_name,
        region,
        cluster.kubernetes_version,
        kb_version
    ))
    if input().upper() != "YES":
        print("\nUser aborted upgrade request.\n\n")
        exit(0)


print("\n\nSubmitting upgrade request for cluster {} in child compartment {} within region {}\n".format(
    cluster_name,
    child_compartment_name,
    region
))

# ok, upgrade the k8s backplane version
update_cluster_response = upgrade_kubernetes_backplane(
    container_client,
    UpdateClusterDetails,
    cluster.id,
    kb_version
)

print("The upgrade of cluster {} from version {} to version {} has been started.\n".format(
        cluster_name,
        cluster.kubernetes_version,
        kb_version))

