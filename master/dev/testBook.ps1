$region              	= "us-ashburn-1"
$parent_compartment  	= "afritz_root" 
$child_compartment   	= "learning"
$vcn_name            	= "Demo"
$subnetwork_name     	= "Private Subnet-Demo"
$ad_number           	= 2
$Database_Container  	= "TSTMGR"
$DB_Name             	= "TSTMGR"
$PDB_Name            	= "TSTMGR_PDB"
$DB_PWD              	= "Ex#57T-EdwhjjB6nWRhQa"
$workload 		= "OLTP"
$storage_type 		= "ASM"
$service_node_name   	= "afztstnode"
$storage_size		= "256"
$node_count 		= "1"
$SSH_public_key_file 	= "/home/ansible/.ssh/afz_rsa.pub" 
$time_zone		= "America/New_York"
$database_edition 	= "ENTERPRISE_EDITION"
$database_version	= "19.15.0.0"
#$shape 		= "VM.Standard.E4.Flex"
$shape 		 	= "VM.Standard2.2"
$license_model 		= "LICENSE_INCLUDED"
$private_ip		= "10.254.1.24"

#echo /files/Oci-AddDbSystemX.py $parent_compartment  $child_compartment $vcn_name $subnetwork_name  $ad_number $Database_Container $DB_Name $PDB_Name $workload $storage_type  $service_node_name $storage_size $node_count $SSH_public_key_file $time_zone $DB_PWD $database_edition $database_version $shape $license_model $region $private_ip

/files/Oci-AddDbSystem.py $parent_compartment  $child_compartment $vcn_name $subnetwork_name  $ad_number $Database_Container $DB_Name $PDB_Name $workload $storage_type  $service_node_name $storage_size $node_count $SSH_public_key_file $time_zone $DB_PWD $database_edition $database_version $shape $license_model $region $private_ip
