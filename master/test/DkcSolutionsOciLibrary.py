import datetime
import subprocess
import json
import oci
import os
import sys
import time
from collections import defaultdict

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

# functions
def AddToRouteTable(virtual_network_client, virtual_network_composite_ops, myVcn, myRouteTable_id, myEntity_id, myTargetCidr):
    '''
    This function begins by obtaining existing route table data from the route table, then creates a route rule dict. The dict object
    is then appended along with the new route rule to route_rules. route_rules is then applied as an update to the route table
    via update_route_table_and_wait_for_state.
    '''

    get_route_table_response = virtual_network_client.get_route_table(myRouteTable_id)
    if get_route_table_response is None:
        return bool(False)

    route_rule = oci.core.models.RouteRule(
        cidr_block = None,
        destination = myTargetCidr,
        destination_type = 'CIDR_BLOCK',
        network_entity_id = myEntity_id
    )
    route_rules = get_route_table_response.data.route_rules
    route_rules.append(route_rule)
    
    update_route_table_details = oci.core.models.UpdateRouteTableDetails(route_rules=route_rules)

    update_route_table_response = virtual_network_composite_ops.update_route_table_and_wait_for_state(
        myRouteTable_id,
        update_route_table_details,
        wait_for_states=[oci.core.models.RouteTable.LIFECYCLE_STATE_AVAILABLE]
    ).data
    print(update_route_table_response)
    if update_route_table_response is None:
        return bool(False)
    else:
        return update_route_table_response

def CreateCompartment(ParentCompartment_id, myCompartmentName, myCompartmentDescription):
    '''
    This function calls the OCI CLI wrapper to create a compartment, and prints the results.
    object.
    '''
    cmd = 'oci iam compartment create --compartment-id "'+ParentCompartment_id+'" --name "'+CompartmentName+'" --description "'+CompartmentDescription+'"'
    print(cmd)
    sp  = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=None)
    output, _ = sp.communicate()
    time.sleep(15)
    print(output.decode("utf-8"))
    print("\n")

def CreateInternetGateway(virtual_network_composite_ops, compartment_id, myVcn_id, myInternetGatewayName):
    '''
    This function creates and enables an internet gateway within the selected compartment for the specified
    VCN.
    '''
    create_irg_details = oci.core.models.CreateInternetGatewayDetails(
        compartment_id = compartment_id,
        vcn_id = myVcn_id,
        display_name = myInternetGatewayName,
        is_enabled = True
    )

    create_irg_results = virtual_network_composite_ops.create_internet_gateway_and_wait_for_state(
        create_irg_details,
        wait_for_states=[oci.core.models.InternetGateway.LIFECYCLE_STATE_AVAILABLE]
    ).data
    return(create_irg_results)

def CreateLpg(virtual_network_composite_ops, compartment_id, myVcn, myLpgName):
    '''
    This function creates an LPG within the specified compartment for the specified VCN
    '''
    create_lpg_details = oci.core.models.CreateLocalPeeringGatewayDetails(
        compartment_id = compartment_id,
        vcn_id = myVcn.id,
        display_name = myLpgName
    )
    create_lpg_results = virtual_network_composite_ops.create_local_peering_gateway_and_wait_for_state(
        create_lpg_details,
        wait_for_states=[oci.core.models.LocalPeeringGateway.LIFECYCLE_STATE_AVAILABLE]
    ).data
    if create_lpg_results is None:
        return bool(False)
    else:
        return create_lpg_results

def CreateLpgPeer(myLpgSource_id, myNetworkEntity_id):
    '''
    This function relies on the OCI CLI wrapper to create the LPG and returns the result to the calling program
    '''
    cmd = 'oci network local-peering-gateway connect --local-peering-gateway-id '+myLpgSource_id+' --peer-id '+myNetworkEntity_id
    print(cmd)
    sp  = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=None)
    output, _ = sp.communicate()
    time.sleep(15)
    print(output.decode("utf-8"))
    results = json.loads(output.decode("utf-8"))
    print("\n")
    return results

def CreateNatGateway(virtual_network_composite_ops, compartment_id, myVcn_id, myNatGatewayName):
    '''
    This function creates a NAT gateway within the specified compartment for the specified VCN
    '''
    create_natgateway_details = oci.core.models.CreateNatGatewayDetails(
        compartment_id = compartment_id,
        display_name = myNatGatewayName,
        vcn_id = myVcn_id
    )

    create_natgateway_results = virtual_network_composite_ops.create_nat_gateway_and_wait_for_state(
        create_natgateway_details,
        wait_for_states=[oci.core.models.NatGateway.LIFECYCLE_STATE_AVAILABLE]
    ).data
    return create_natgateway_results

def CreateRouterTable(virtual_network_composite_ops, myVcn, myLpg_id, myRouteTname, myTargetCidr):
    '''
    This function creates a router table.
    THERE IS NO ONLINE SOURCE EXAMPLES, SO PAY ATTENTION TO THE FOLLOWING COMMENTS.

    First, we create a router rule. You can create a router table using the console without a
    router rule, but you cannot do the same with the API. The model create_route_table_and_wait_for_state
    expects the router rule to be an array, even if there is only 1 rule. There is no code source for
    oci.core.models.RouteRule, and it does not create a dictionary (dict) object in array form. It only creates
    a single dict object. So we create the dict object using oci.core.models.RouteRule. Next,
    we create an array called "route_rules" and use the append method to append the array with the object.
    The array route_rules is then passed to CreateRouteTableDetails to the dict being formed by
    CreateRouteTableDetails in a format that is acceptable to Create_route_table_and_wait_for_state.
    We then pass create_route_table_details to Create_route_table_and_wait_for_state as you
    would expect for any OCI composite module, get and return the results to the calling code.
    '''
    route_rule = oci.core.models.RouteRule(
        destination = myTargetCidr,
        destination_type = 'CIDR_BLOCK',
        network_entity_id = myLpg_id
    )

    route_rules = []
    route_rules.append(route_rule)

    create_route_table_details = oci.core.models.CreateRouteTableDetails(
        compartment_id = myVcn.compartment_id,
        display_name = myRouteTname,
        route_rules = route_rules,
        vcn_id = myVcn.id
    )
    # print(create_route_table_details) # remove comment when debugging

    create_router_table_results = virtual_network_composite_ops.create_route_table_and_wait_for_state(
        create_route_table_details,
        wait_for_states=[oci.core.models.RouteTable.LIFECYCLE_STATE_AVAILABLE]
    ).data
    if create_router_table_results is None:
        return bool(False)
    else:
        return create_router_table_results

def CreateSubnet(virtual_network_composite_ops, myVcn, mySubnetName, mySubnetDnsName, mySubnetCidr):
    '''
    This function creates a subnet within the specified compartment for the specified VCN
    '''
    create_subnet_details = oci.core.models.CreateSubnetDetails(
        compartment_id = myVcn.compartment_id,
        cidr_block = mySubnetCidr,
        display_name = mySubnetName,
        dns_label = mySubnetDnsName,
        vcn_id = myVcn.id
    )
    create_subnet_response = virtual_network_composite_ops.create_subnet_and_wait_for_state(
        create_subnet_details,
        wait_for_states=[oci.core.models.Subnet.LIFECYCLE_STATE_AVAILABLE]
    ).data
    if create_subnet_response is None:
        return bool(False)
    else:
        return create_subnet_response

def CreateVcn(virtual_network_composite_ops, compartment_id, myVcnName, myVcnDnsName, myCidrBlock):
    '''
    This function creates a VCN within the specified compartment, names it as defined by myVcnName, and applies the
    CIDR myCidrBlock to the VCN.
    '''
    create_vcn_details = oci.core.models.CreateVcnDetails(
        cidr_block = myCidrBlock,
        compartment_id = compartment_id,
        display_name = myVcnName,
        dns_label = myVcnDnsName
    )

    create_vcn_response = virtual_network_composite_ops.create_vcn_and_wait_for_state(
        create_vcn_details,
        wait_for_states=[oci.core.models.Vcn.LIFECYCLE_STATE_AVAILABLE]
    ).data
    if create_vcn_response is None:
        return bool(False)
    else:
        return create_vcn_response

def CreateVolume(compartment_id, 
                        myAvailabilityDomain, 
                        myDisplayName, 
                        mySizeInGb,
                        myVCPUs):
    '''
    We choose to call the OCI wrapper instead of the API in this case due to:
        1) There is no method to build volume details in a dict prior to calling create_volume_and_wait_for_state
        2) There is no option to define the performance metric of the volume prior to creation
    After volume creation, we print results and return to the calling program.
    '''
    cmd = 'oci bv volume create --availability-domain '+myAvailabilityDomain+' --compartment-id '+compartment_id+' --display-name '+myDisplayName+' --size-in-gbs '+str(mySizeInGb)+' --vpus-per-gb '+str(myVCPUs)
    sp  = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=None)
    output, _ = sp.communicate()
    print(output.decode("utf-8"))

def DeleteSubnet(virtual_network_composite_ops, mySubnet_id):
    '''
    This function removes a subnet from the specified VCN within the specified compartment
    '''
    results = virtual_network_composite_ops.delete_subnet_and_wait_for_state(
        mySubnet_id,
        wait_for_states=[oci.core.models.Subnet.LIFECYCLE_STATE_TERMINATED]
    )
    print('Deleted Subnet: {}'.format(mySubnet_id))
    print()

def DeleteVcn(virtual_network_composite_ops, myVcn_id):
    '''
    This function removes the specified VCN within the specified compartment.
    '''
    virtual_network_composite_ops.delete_vcn_and_wait_for_state(
        myVcn_id,
        wait_for_states=[oci.core.models.Vcn.LIFECYCLE_STATE_TERMINATED]
    )

    print('Deleted VCN: {}'.format(myVcn_id))
    print()

def GetAvailabilityDomains(identity_client, compartment_id):
    '''
    We use OCI in this case to get the availability domains and return an array of AD names
    '''

    '''
    This code snippet is very important for workarounds when we have to rush to get something
    done while waiting on Oracle support to an answer to a reported issue.

    cmd = 'oci iam availability-domain list --compartment-id '+compartment_id
    sp  = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=None)
    output, _ = sp.communicate()
    results   = json.loads(output.decode("utf-8"))
    RETURN = []
    RETURN = [results["data"][0]["name"],results["data"][1]["name"],results["data"][2]["name"]]
    return RETURN
    '''
    results = identity_client.list_availability_domains(compartment_id).data
    if results is None:
        return bool(False)
    else:
        return results

def GetActiveCompartment(myParentCompartments, myCompartmentName):
    '''
    Get an active compartment by name
    '''
    for r in myParentCompartments:
        if r.name == myCompartmentName and r.lifecycle_state == "ACTIVE":
            return (r)

def GetAuditConfiguration(audit_client, my_tenant_id):
    '''
    This function retrieves the current audit setting for the tenant
    '''
    results = audit_client.get_configuration(my_tenant_id).data
    if results is None:
        return bool(False)
    else:
        return results

def GetCompartments(identity_client,compartment_id):
    '''
    Gets all child compartments of the parent
    '''
    results = identity.list_compartments(compartment_id).data
    if results is not None:
        return results
    else:
        return bool(False)

def GetBackupPolicies(block_storage_client, compartment_id):
    '''
    Get all backup policies in the compartment
    '''
    results = block_storage_client.list_volume_backup_policies(compartment_id=compartment_id).data
    if results is not None:
        return results
    else:
        return bool(False)

def GetDbNodeName(database_client, compartment_id, myDbNode_id):
    '''
    Returns all DB nodes that are attached to a Db System.
    '''
    results = database_client.list_db_nodes(compartment_id, db_system_id = myDbNode_id).data
    if results is not None and results[0].lifecycle_state != "TERMINATED":
        return results
    else:
        return bool(False)

def GetDbSystems(database_client, compartment_id, myDbSystemName):
    '''
    Returns all of the DB Systems that are members of the compartment regardless of life-cycle state
    '''
    db_systems_list = database_client.list_db_systems(compartment_id).data
    if db_systems_list is None:
        return bool(False)
    else:
        return db_systems_list

def GetDbSystem(database_client, compartment_id, myDbSystemName):
    '''
    Returns the DB System that is a member of the compartment and is not terminated
    '''
    db_systems_list = database_client.list_db_systems(compartment_id).data
    for dbs in db_systems_list:
        if dbs.display_name == myDbSystemName and dbs.lifecycle_state != "TERMINATED":
            return dbs

def GetIgws(virtual_network_client, compartment_id, myVcn_id):
    '''
    This function returns a list of internet gateways within the compartment for the specified VCN OCID
    '''
    results = virtual_network_client.list_internet_gateways(compartment_id, myVcn_id).data
    if results is None:
        return bool(False)
    else:
        return results

def GetIgw(myListOfInternetGateways, myInternetGatewayName):
    '''
    Function returns the internet gateway from the dict object list if found
    '''
    for igw in myListOfInternetGateways:
        if igw.display_name == myInternetGatewayName:
            return igw

def GetLPGs(virtual_network_client, compartment_id, myVcn_id):
    '''
    Returns all LPGs within a compartment that are associated with a VCN
    '''
    results = virtual_network_client.list_local_peering_gateways(compartment_id, myVcn_id).data
    if results is None:
        return bool(False)
    else:
        return results

def GetLpg(virtual_network_client, compartment_id, myVcn_id, myLpgName):
    '''
    Returns the LPG that matches myLpgName that is in the compartment and is also associated with the VCN
    '''
    list_of_lpgs = virtual_network_client.list_local_peering_gateways(compartment_id, myVcn_id).data
    results = []
    for l in list_of_lpgs:
        if l.display_name == myLpgName and l.lifecycle_state == "AVAILABLE":
            results.append(l)
    if results is None:
        return bool(False)
    else:
        return results

def GetNgws(virtual_network_client, compartment_id):
    '''
    This function returns all NAT gateways within the compartment. Note that the API does not
    accept a VCN OCID in its argument vector. This is inconsistent with nearll all OCI APIs.
    '''
    results = virtual_network_client.list_nat_gateways(compartment_id).data
    if results is None:
        return bool(False)
    else:
        return results

def GetNgw(myCompartmentNatGateways, myNatGatewayName):
    '''
    Function returns the nat gateway from the list of nat gateways if found
    '''
    for ngw in myCompartmentNatGateways:
        if ngw.display_name == myNatGatewayName:
            return ngw

def GetRouteTables(virtual_network_client, compartment_id, myVcn_id):
    '''
    Returns all router tables in the compartment that are associated with the VCN
    '''
    results = virtual_network_client.list_route_tables(compartment_id, myVcn_id).data
    if results is None:
        return bool(False)
    else:
        return results

def GetRouteTable(virtual_network_client, compartment_id, myVcn_id, myRouteTableName):
    '''
    Returns the router table that matches myRouterTableName that is in the compartment and is also associated with the VCN
    '''
    list_of_router_tables = []
    list_of_router_tables = virtual_network_client.list_route_tables(compartment_id, myVcn_id).data
    for l in list_of_router_tables:
        if l.display_name == myRouteTableName and l.lifecycle_state == "AVAILABLE":
            return l

def GetSubnets(virtual_network_client, myCompartment, myVcn):
    '''
    Returns a list of subnets associated with a VCN within a compartment
    '''
    results = virtual_network_client.list_subnets(myCompartment, myVcn).data
    if results is not None:
        return results
    else:
        return bool(False)
    #return results

def GetSubnet(virtual_network_client, myCompartment, mySubnets, mySubnetName):
    '''
    Gets a subnet associated with a VCN within a compartment
    '''
    for r in mySubnets:
        if r.display_name == mySubnetName and r.lifecycle_state == "AVAILABLE":
            results = virtual_network_client.get_subnet(r.id).data
            if results is not None:
                return results
            else:
                return bool(False)

def GetSubscriptionRegions(identity, tenancy_id):
    '''
    To retrieve the list of all available regions.
    '''
    list_of_regions = []
    list_regions_response = identity.list_region_subscriptions(tenancy_id)
    if list_regions_response is None:
        return bool(False)
    for r in list_regions_response.data:
        list_of_regions.append(r)
    return list_of_regions

def GetVcn(virtual_network_client, myVcns, myVcnName):
    '''
    To retrieve data on a specific VCN
    '''
    for r in myVcns:
        if r.display_name == myVcnName and r.lifecycle_state == "AVAILABLE":
            results = virtual_network_client.get_vcn(r.id).data
            if results == r:
                return results
            else:
                return bool(False)

def GetVcns(virtual_network_client, compartment_id): # remove identity and test
    '''
    To retrieve a list of all VNCs within the specified compartment
    '''
    results = virtual_network_client.list_vcns(compartment_id).data
    if results is not None:
        return results
    else:
        return bool(False)

def GetVMs(compartment_id):
    '''
    To retrieve the list of all VMs within a compartment
    '''
    results = compute_client.list_instances(compartment_id=compartment_id).data
    if results is not None:
        return results
    else:
        return bool(False)

def GetVm(compute_client, myVMs, myVmName):
    '''
    Retrieves data about a specific VM
    '''
    for r in myVMs:
        if r.display_name == myVmName and r.lifecycle_state != "TERMINATED":
            results = r
            if results is None:
                return bool(False)
            else:
                return results

def GetVmBlockVol(block_storage_client,compute_client, compartment_id, myVM):
    '''
    Gets the block volumes that is attached to a VM
    First we get the block volume attachments, then enter a loop to append to block_vol_list
    all block volumes found that match the instance OCID
    '''
    blockvol_attachment = compute_client.list_volume_attachments(compartment_id).data
    if blockvol_attachment is None:
        return bool(False)
    block_vol_list = []
    for r in blockvol_attachment:
        if r.instance_id == myVM.id:
            block_vol_list.append(r)
    if block_vol_list is None:
        return bool(False)
    else:
        return block_vol_list

def GetVmBootVol(block_storage_client,compute_client, compartment_id, myVM):
    '''
    Gets the boot volume that is attached to a VM
    First we get the boot volume attachment, then we pass the correct params to get_boot_volume
    '''
    bootvol_attachment = compute_client.list_boot_volume_attachments(myVM.availability_domain, compartment_id).data
    if bootvol_attachment is None:
        return bool(False)
    results = block_storage_client.get_boot_volume(bootvol_attachment[0].boot_volume_id).data
    if results is not None:
        return results
    else:
        return bool(False)

def GetVmBootVolBackups(block_storage_client, compartment_id, VmBootVol_id):
    '''
    Get all VM backups for the specified boot volume ID within the compartment. The API will only report
    block volume backups for the specified region in the dict config. For example, to get all backups for
    the region US-PHOENIX-1, do this prior to calling the function:
    config['region']        = 'US-PHOENIX-1' 
    Then make the API call.
    
    IMPORTANT
    Don't forget to return to the default after the function has returned its results as in:
    config                  = oci.config.from_file()
    Danger to those who are not mindful of this API requirement
    '''
    bootvol_backup_list = []
    results = block_storage_client.list_boot_volume_backups(compartment_id).data
    for r in results:
        if r.boot_volume_id == VmBootVol_id:
            bootvol_backup_list.append(r)
    if bootvol_backup_list is None:
        return bool(False)
    else:
        return bootvol_backup_list

def GetVmBlockVolBackups(block_storage_client, compartment_id, myVmBlockVolumes):
    '''
    Get all VM backups for the specified boot volume ID within the compartment. The API will only report
    block volume backups for the specified region in the dict config. For example, to get all backups for
    the region US-PHOENIX-1, do this prior to calling the function:
    config['region']        = 'US-PHOENIX-1' 
    Then make the API call.
    
    IMPORTANT
    Don't forget to return to the default after the function has returned its results as in:
    config                  = oci.config.from_file()
    Danger to those who are not mindful of this API requirement
    '''
    results = block_storage_client.list_volume_backups(compartment_id).data
    blockvol_backup_list = []
    '''
    In this logic, we must account for the possibility that a VM may have more than one block volume attached
    to it. We walk down myVmBlockVolumes, then for each block volume, we walk down results and append to
    blockvol_backup_list any objects that match the OCID of the volume found in myVmBlockVolumes.
    '''
    for b in myVmBlockVolumes:
        for r in results:
            if r.volume_id == b.volume_id:
                blockvol_backup_list.append(r)
    if blockvol_backup_list is None:
        return bool(False)
    else:
        return blockvol_backup_list

def SelectBackupPolicy(block_storage_client, myBackupPolicies, myBackupPolicyName):
    '''
    Selects the volume backup policy in the compartment that matches myBackupPolicyName
    '''
    results = []
    for p in myBackupPolicies:
        if p.display_name == myBackupPolicyName:
            ReturnValue = block_storage_client.get_volume_backup_policy(p.id).data
            if ReturnValue is not None:
                results.append(ReturnValue)
    if results is None:
        return bool(False)
    else:
        return results

def SelectBlockVolume(block_storage_client, myBlockVolumes, myBlockVolumeName):
    '''
    This function returns the complete data set associated with the block volume that matches
    myBlockVolumeName. Please note this is the only way to get the display name of a block
    volume. The function only returns block volumes that are in an AVAILABLE state.
    '''
    results = []
    volume_list = []
    for bv in myBlockVolumes:
        volume_list.append(block_storage_client.get_volume(bv.volume_id).data) # This is how we only get volumes associated with a VM
    if volume_list is None:
        return bool(False)
    for vl in volume_list:
        if vl.display_name == myBlockVolumeName and vl.lifecycle_state == "AVAILABLE":
            results.append(vl)
    if results is None:
        return bool(False)
    else:
        return results

# end of functions

'''
The following must be in every OCI python script. Setting these environment vars suppresses certain types of
warnings. It is a good practice to uncomment when debugging code.
'''
# Set env, see https://github.com/oracle/oci-cli/blob/master/src/oci_cli/cli_root.py line 35, 249, 250
os.environ["OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNIN"] = "TRUE"
os.environ["SUPPRESS_PYTHON2_WARNING"] = "TRUE"

# See https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/quickstart.html for example
'''
The method oci.config.from_file() reads the default $home/.oci/config file, unless otherwise specified, and
returns its contents
'''
config          = oci.config.from_file()


'''
identity becomes a method as defined by oci.identity.IdentityClient(). Note how we pass config to it.
This method is used by many OCI methods and decorators.
'''
identity = oci.identity.IdentityClient(config)

'''
We extract the tenancy OCID from config as a simple string. The tenancy is in fact the root compartment.
See https://docs.cloud.oracle.com/en-us/iaas/Content/Identity/Tasks/managingcompartments.htm
for an explaination of how compartments work in OCI.
'''
my_tenant_id = (config["tenancy"])          # the tenancy OCID and the root compartment OCID are the same thing

'''
We declare methods that will be used when making calls to the OCI REST APIs
The client method is used to perform operations on cloud objects.
The composite method is used to create dict objects that are passed to client methods for MACDs
'''

audit_client            = oci.audit.AuditClient(config)
audit_composite_ops     = oci.audit.AuditClientCompositeOperations(audit_client)
block_storage_client    = oci.core.BlockstorageClient(config, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
block_composit_ops      = oci.core.BlockstorageClientCompositeOperations(block_storage_client)
compute_client          = oci.core.ComputeClient(config, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
compute_composite_ops   = oci.core.ComputeClientCompositeOperations(compute_client)
database_client         = oci.database.DatabaseClient(config, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
database_composite_ops  = oci.database.DatabaseClientCompositeOperations(database_client)
identity_client         = oci.identity.IdentityClient(config, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
identity_composit_ops   = oci.identity.IdentityClientCompositeOperations(identity_client)
virtual_network_client  = oci.core.VirtualNetworkClient(config, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
virtual_network_composite_ops = oci.core.VirtualNetworkClientCompositeOperations(virtual_network_client)

'''
We always want to have the regions the subscrition is subscribed to as well as the availability domain names
'''
my_audit_settings       = GetAuditConfiguration(audit_client,my_tenant_id)                      # Get global audit retention setting
region_info             = GetSubscriptionRegions(identity,my_tenant_id)                         # Get regions the subscription is subscribed to
availability_domains    = GetAvailabilityDomains(identity_client, my_tenant_id)                 # Get availability domains for the region
