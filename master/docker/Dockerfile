#################################################################################################
#                                           INSTRUCTIONS                                        #
#################################################################################################
#
#       These instructions will show you how to install the David Kent Cloud Solutions
#       OCI Express Cloud Administrator's Utilities onto your desktop. The entire process
#       start to finish should take about 15 minutes to complete.
#
# 1.    Install docker desktop onto your cloud administrator machine. You can get docker
#       desktop from https://www.docker.com/products/docker-desktop . For a Linux
#       installation, you can install for your Linux distro per
#       https://docs.docker.com/engine/install/ . If your OS is Oracle Linux Enterprise,
#       we recommend that you simply install with yum with the command below:
#                           sudo yum install docker -y
#
# 2.    Start by adding the microservice kernel to your repository. Use of a Fedora, Redhat,
#       or Oracle kernel is supported. Note however our primary development kernel is Oracle
#       Linux. We support kernels from version 7.5 and above. To pull the microservice kernel,
#       run "docker pull oraclelinux:x.x", where x.x is the major version of the microservice
#       kernel image to deploy on. For example, "docker pull oraclelinux:8.3" will pull
#       the version 8.3 kernel.
#
# 3.    Create a parent directory where you will build the container image from. We recommend
#       that you pick a directory that is separate from other development you may be doing
#       but is closely linked to other code. For example, I install my docker build files
#       starting at /home/hank/GitHub/DKC/docker, and I have my projects stored in branches
#       under /hone/hank/GitHub/DKC in other child directories where I have projects and
#       branches copied to. This makes it easy for me to push the Docker file to GitHub
#       and available for others to see and work on it.
#
# 4.    You'll need a copy of the codebase and this Dockerfile configuration file. This is
#       downloadable from the same GitHub repository that you downloaded this file from.
#       Of course, you must have permission to the repository to get the code since it is
#       not free or open source. If you have rights to the code but do not have access to
#       the codebase, contact your David Kent Cloud Solutions sales rep, and she/he will
#       be more than happy to get your access established. The code base is in two forms.
#       A zip file called KENT.zip is what you'll need to put in the same directory as
#       this docker file. The actual code should be copied to a location where you store
#       other code for other development work. Do not store any raw source code in the
#       directory where you are building the container image from.

# 5.    From this directory where the KENT.zip fiile and this Dockerfile is stored, run
#       the command "docker build -t <image name> ." to create the image into your
#       docker repository. For example, the command could be:
#
#       docker build -t kentcollegedkimagefile .
#
#       You'll note there are no upper case, spaces, or special charecters in the image
#       name. This is important.
#
# 6.    Now you'll need to launch a container from the image you have just built. So
#       that you better understand how this works, the container is the sum of the
#       base image, the image you just created in step 5, plus the container. The
#       container name could be the same as the image name, or whatever you want to
#       name it. For the sake of these instructions, we'll name it "throwitaway"
#       since this first container is only temporary. We will not be saving it.
#       Run the command below:
#
#       docker container run -d -ti --name throwitaway --hostname temphost kentcollegedkimagefile
#
# 7.    Now let's make sure the container is running. Run the command below:
#
#       docker container ls
#
# 8.    Connect to the container as the user "ansible" with this command:
#
#       docker container exec -it throwitaway bash -c 'su - ansible'

# 9.    Now, follow the instructions at https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm
#       to install the latest version of the OCI client. For the sake of simplicity, we do this in two
#       commands. The first command pulls the utility from github and does the base install. The second
#       command configures the OCI client to your OCI tenancy and user ID. Note we do not recommend using
#       a cloud adminstrator user ID for cloud orchestration tasks. For cloud orchestration, you should
#       be using a service account. If you are not sure of what this is, please reach out to your
#       assigned David Kent Cloud Solutions consultant for help.
#
#       bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
#
# 10.   Once you have completed the setup and have verified that you can connect to your tenancy with the
#       codebase, exit the container with a CTL-d command and return to your operating system's shell
#       prompt. Run the command below to get the ID of the container "throwitaway". You'll need this ID
#       for the next task.
#
#       docker container ps
#
# 11.   Now you'll create a permanent image from the container "throwitaway" using this command:
#       "docker container commit -p <container id> <new image name>". For the sake of instruction,
#       an example of the command is below. Substitute the example image name with your desired
#       image name.
#
#       docker container commit -p 1d63fd23f870 davidkentcloudsolutions/ociexpressutils:B2.1b
#
# 12.   Now push the container to the docker private repository, then clean-up your docker environment.
#
#       docker push davidkentcloudsolutions/ociexpressutils:B2.1b
#       docker container rm throwitaway --force
#       docker image rm kentcollegedkimagefile
#
# 13.   On the client's VM, install Docker, then pull the container, then list it
#
#       docker pull davidkentcloudsolutions/ociexpressutils:B2.1b
#
# 12.   Now launch a container from your image and connect to it. The container will immediately
#       work without any configuration:
#
#       docker container run -d -ti --hostname kentanst01 \
#           --memory="2g" \
#           --restart always \
#           --name kentcollegemycontainer \
#           -v $(pwd):/files \
#           davidkentcloudsolutions/ociexpressutils:B2.1b
#       docker container exec -it kentcollegemycontainer bash -c "su - ansible"
#
#       Note the above when used with '--restart always' will always restart the container when docker restarts, or if the container core dumps.
#       Omit this option if you desire to manually start and stop the container.
#
# 13.   All of the images and the containers will be retained EXCEPT for throwitaway. Let's throw it away:
#
#       docker container stop throwitaway
#       docker container rm throwitaway
#
# 14.   You can now use the docker dashboard or "docker container start/stop" to start or stop your container.
#       See the David Kent Cloud Solutions OCI Express Cloud Administrator's Utilities documentation or speak
#       with your assigned David Kent Cloud Solutions consultant for help with using the utilities.
#
#       You should become familiar with Docker. There are two courses from Udemy that I recommend. For beginners:
#       "Docker for the Absolute Beginner - Hands On - DevOps"
#
#       And for developers, I recommend:
#       "Docker Mastery: with Kubernetes +Swarm from a Docker Captain"

FROM oraclelinux:8.3
# Define Args and Env needed to create links
ENV PS_INSTALL_FOLDER=/opt/microsoft/powershell/7 \
    # Define ENVs for Localization/Globalization
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false \
    C_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8

ADD https://github.com/PowerShell/PowerShell/releases/download/v7.1.0/powershell-7.1.0-1.rhel.7.x86_64.rpm \
    /tmp/powershell-linux.rpm

# update the system and install required RPMs
RUN yum update -y \
   && yum install cronie -y \
   && yum install git -y \
# must be installed before powershell
   && yum install icu.x86_64 libicu-devel.x86_64 -y
RUN rpm -ivh /tmp/powershell-linux.rpm
RUN yum install python3 -y \
   && yum install python38-pip -y \
   && yum install unzip -y \
   && yum install vim -y
RUN ln -s /usr/bin/python3 /usr/bin/python \
   && ln -s /usr/bin/pip3 /usr/bin/pip

RUN useradd ansible \
   && su - ansible -c "pip install pandas --user" \
   && su - ansible -c "pip install tabulate --user" \
   && su - ansible -c "pip install detect_delimiter --user" \
   && su - ansible -c "pip install oci --user" \
   && su - ansible -c "pip install ansible --user"

# install the codebase and required python modules, create the ansible user
COPY KENT.zip .
RUN unzip -o KENT.zip \
   && chmod 755 /bin/Oci*.py \
   && su - ansible -c "ln -s /bin/*.py ."
