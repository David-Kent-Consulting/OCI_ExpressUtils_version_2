$myEnv = Get-Content -Path "environment.json" | ConvertFrom-Json -AsHashtable
$Env:HOSTNAME = $myEnv.HOSTNAME
$Env:ANSIBLE_LIB_PATH = $myEnv.ANSIBLE_LIB_PATH
$Env:PATH = $myEnv.PATH
$Env:HOME = $myEnv.HOME
$Env:XDG_DATA_DIRS = $myEnv.XDG_DATA_DIRS
$Env:PKG_CONFIG_PATH = $myEnv.PKG_CONFIG_PATH
$LibPath = Get-ChildItem -Path env:ANSIBLE_LIB_PATH
$Path = $LibPath.Value

Set-Location $Path

ansible-playbook 1000_BackupDatabases.yaml