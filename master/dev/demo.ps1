


$region = "us-ashburn-1"
$parent_compartment_name = "admin_comp"

function create_vcn(
    $my_parent_compartment_name,
    $my_child_compartment_name,
    $my_vcn_name,
    $my_vcn_dns_name,
    $my_cidr_block,
    $my_region
){
    $results = Start-Process -FilePath ./Oci-AddVirtualCloudNetwork.py -ArgumentList `
        $my_parent_compartment_name,
        $my_child_compartment_name,
        $my_vcn_name,
        $my_vcn_dns_name,
        $my_cidr_block,
        $my_region
      #  '--force'
}

# Create the VCNs
create_vcn $parent_compartment_name auto_comp auto_vcn autovcn "10.1.0.0/24" $region
create_vcn $parent_compartment_name bas_comp  bas_vcn  basvcn  "10.1.1.0/24" $region
    