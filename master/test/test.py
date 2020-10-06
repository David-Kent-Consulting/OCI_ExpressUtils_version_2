import os
import sys

key_files = '/Users/henrywojteczko/Documents/GitHub/NWMSU/master/test/ssh_key_files'
entries = os.listdir(key_files)
ssh_keys = []
for entry in entries:
    file_name = key_files+"/"+entry
    print(file_name)
    with open(file_name, mode='r') as file:
        ssh_key = file.read()
        ssh_keys.append(ssh_key)
    print(ssh_keys)