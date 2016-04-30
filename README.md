# OJO Bot

This is a prototype data processor/publisher for NASA. 

Maintained by Pat Cappelaere	
Vightel Corporation
pat@cappelaere.com

NOTE:  Some changes have been made to the code to run on a local server without required access to the AWS cloud.
Check config/config.yaml
using_aws_s3_for_storage could be set to 0

Check python/config.py for example...
USING_AWS_S3_FOR_STORAGE	= 1
USING_LOCAL_DIR_FOR_STORAGE	= 1
LOCAL_DIR_STORAGE			= "/Users/patricecappelaere/Development/ojo/tmp"

NOTE 2: This may not be the best option to run as an enterprise system with multiples instances and load balancing.

## Pre-requisites

Check PREREQUISITES.md

## Local Docker
Install docker and start VM
Start Docker VM via Docker Quickstart Terminal
> docker --version
Docker version 1.11.0

> docker-machine env default
> bash
> eval "$(docker-machine env default)"
> docker ps

### Build locally
> docker-compose build development
> docker images

Start shell in development mode... you can start processing python scripts
> docker run -i -p 7465:7465 -t ojobot_development /bin/bash

To test python scripts using shared folder
> docker run -i -p 7465:7465 -v /Users/patrice/data:/app/user/data2 -v /Users/patrice/Development/ojo/ojo-bot/python:/app/user/pydev -t ojobot_development  /bin/bash

To stop a docker process
> docker ps
> docker stop CONTAINER_ID

### Connecting to service
Start Chrome and use IP address of VM returned by docker-machine env default
> http://192.168.99.100:7465/

### Checking/Cleaning docker images
> docker images

Clean Docker
> docker rm -v $(docker ps -a -q -f status=exited)

> docker rmi -f $(docker images | grep "<none>" | awk "{print \$3}")
	
> docker rmi $(docker images -f "dangling=true" -q)

### Building base container
> docker-compose build conda

Test it:
> docker-compose run conda

Tag it
> docker images

> docker tag 608fd2eb4b79 cappelaere/ojo_publisher_base_stack:v1

Push it
> docker login

> docker push cappelaere/ojo_publisher_base_stack

