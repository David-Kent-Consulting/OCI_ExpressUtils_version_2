#export HOSTNAME=nwmsuansp01
#export SHELL=/bin/bash
#export USER=ansible
#export LD_LIBRARY_PATH=/opt/rh/rh-python36/root/usr/lib64
#export ANSIBLE_LIB_PATH=/home/ansible/PPRD
#export PATH=/home/ansible/bin:/opt/rh/rh-python36/root/usr/bin:/home/ansible/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/home/ansible/.local/bin:/home/ansible/bin
#export HOME=/home/ansible
#export XDG_DATA_DIRS=/opt/rh/rh-python36/root/usr/share:/home/ansible/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:/usr/local/share:/usr/share
#export PKG_CONFIG_PATH=/opt/rh/rh-python36/root/usr/lib64/pkgconfig


cd /home/ansible/PPRD
pwsh ./1000_StartBannerTestServices.ps1
