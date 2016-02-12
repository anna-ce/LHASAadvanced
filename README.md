# OJO Bot

This is a prototype for NASA. 

Pat Cappelaere	Vightel		pat@cappelaere.com

## Requirements & Installation

npm install

## Set HEROKU Env	
> heroku config:set DATABASE_URL=
> heroku config:set fbAppId=
> heroku config:set fbSecret=
> heroku config:set AWS_ACCESSKEYID=
> heroku config:set AWS_SECRETACCESSKEY=
> heroku config:set AWS_REGION=

## And start
> git push heroku master
> heroku logs --tail --ps postgres --app ojo-bot
	
## Facebook Testing / Tunneling
> ngrok 7465
	This will display the current status of the tunnel and a public URL To use for testing
	You will have to change the Facebook App Setting Website Site URL to point to proper URL

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

### Deploy to Heroku
Note: it uses docker-compose "web"
> heroku docker:release

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


