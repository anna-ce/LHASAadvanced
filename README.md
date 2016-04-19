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

> docker-machine env default
> bash
> eval "$(docker-machine env default)"
> docker ps


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

### Build locally
> docker-compose build development

Start shell
> docker-compose run development		!Note: does not work since there is no port mapping
> docker run -i -p 8080:8080 -t ojobot_development /bin/bash	!Note: Seems to work with curl -i 192.168.99.100:8080
> docker-compose up development			!Note: postgres connection problem


### Checking/Cleaning docker images
> docker images

Clean Docker
> docker rm -v $(docker ps -a -q -f status=exited)

> docker rmi -f $(docker images | grep "<none>" | awk "{print \$3}")
	
> docker rmi $(docker images -f "dangling=true" -q)
