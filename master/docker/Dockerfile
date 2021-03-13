# you must first pull the base image, like "docker pull oraclelinux:8.3"

FROM oraclelinux:8.3
# Define Args and Env needed to create links
ENV PS_INSTALL_FOLDER=/opt/microsoft/powershell/7 \
    # Define ENVs for Localization/Globalization
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false \
    C_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8

ADD https://github.com/PowerShell/PowerShell/releases/download/v7.1.0/powershell-7.1.0-1.rhel.7.x86_64.rpm \
    /tmp/powershell-linux.rpm

RUN yum update -y
RUN yum install icu.x86_64 libicu-devel.x86_64 -y
RUN rpm -ivh /tmp/powershell-linux.rpm
RUN yum install python3 -y
RUN yum install python38-pip -y
RUN yum install unzip -y
RUN yum install cronie -y
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ln -s /usr/bin/pip3 /usr/bin/pip
COPY KENT.zip .
RUN unzip -o KENT.zip
RUN chmod 755 /bin/Oci*.py
RUN useradd ansible
RUN su - ansible -c "pip install pandas --user"
RUN su - ansible -c "pip install tabulate --user"
RUN su - ansible -c "pip install detect_delimiter --user"
RUN su - ansible -c "pip install oci --user"
RUN su - ansible -c "pip install ansible --user"
RUN su - ansible -c "ln -s /bin/*.py ."



# docker build -t my_test_image .

# docker container run -d -ti --name testbuild --hostname mytestbld my_test_image
# docker container exec -it testbuild bash -c "su - ansible"

# see https://www.thegeekdiary.com/how-to-backup-and-restore-docker-containers/

# save final changes as in: docker commit -p [container-id] new_image_name

# then start it as in docker container run -ti new_image_name /bin/sh

# run the container in the background and tab it with a name
# docker container run -d -ti --name testbuild my_test_build

# connect to the container as the service user
# docker container exec -it my_test bash -c "su - ansible"

# make changes

# Now commit them
# docker commit -p <container id> fully_configured

# start it
# docker container run -d -ti --hostname fullrun --memory="3g" --name running_fully_configured fully_configured

# connect to it
# docker container exec -it running_fully_configured bash -c "su - ansible"
# stop the containers and drop my_test_image, we don't need it any more.
# docker container stop running_fully_configured
# docker container rm running_fully_configured

# list all non-running and running containers
# docker ps -a
