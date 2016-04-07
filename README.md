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

## Developer Accounts
Several developer accounts may be necessary to leverage advanced features

### USGS Access

[USGS Registration](https://ers.cr.usgs.gov/register/) to access USGS imagery

### Facebook

[Facebook Developer Site/Registration](https://developers.facebook.com/docs/apps/register) to share products

### Twitter

[Twitter Developer Registration](https://dev.twitter.com/) to share products

### Mapbox

[Mapbox Developer Registration](https://www.mapbox.com/developers/) for map bacground

### ForecastIO

[Forecast API registration](https://developer.forecast.io/register) for personal forecast at specific location


### Papertrail

[Papertrail Registration](https://papertrailapp.com) For Log aggregation

## Requirements & Installation

npm install

## Set  Env	
Edit the envs.docker.sh.tmpl file, save it as envs.docker.sh and source it

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

### Convox
#### Pre-requisites
Create an Amazon SQS Queue
and Update Environment variables

Lambda functions for scheduling python scripts

Postgresql database to host sessions and landslide inventory

Install new rack from GUI (Takes a while)

Enable SSH
> convox instances keyroll

Check
> convox instances

Scale Up
> convox rack scale --type m3.large

> convox scale web --count 1 

> convox scale web --memory 512

> convox scale worker --count 1 

> convox scale worker --memory 512

Create App
> convox apps create ojo-bot

Check
> convox apps info

> convox instances

Deploy
> convox deploy

Check logs
> convox logs

