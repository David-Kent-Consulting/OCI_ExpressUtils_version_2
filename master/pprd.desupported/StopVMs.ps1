Set-Location /home/ansible/pprd

# shutdown the hosts as first task, OCI APIs hard stop the VM
ansible mesbasp01 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible mesodst01 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible mesodst02 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible messsbt01 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible messsbt02 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible meadmt01 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible mesjsbt01 	--become --become-user root -a "/usr/local/bin/shutdown.sh"
ansible mesdwcat01 	--become --become-user root -a "/usr/local/bin/shutdown.sh"

# wait 10 minutes before calling API to stop compute instances
Start-Sleep 600

# Call the ansible python wrappers that call the OCI APIs and stop the compute instances
ansible-playbook /home/ansible/pprd/100_StopVMs.yaml

Set-Location /home/ansible
