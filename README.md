# OJO Bot

This is an experimental publisher for NASA disaster architecture

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
>git push heroku master
>heroku logs --tail --ps postgres --app ojo-bot
	
## Facebook Testing / Tunneling
> ngrok 7465
	This will display the current status of the tunnel and a public URL To use for testing
	You will have to change the Facebook App Setting Website Site URL to point to proper URL
	
## Local Docker
Install docker and start VM

> docker-machine env default
> bash
> eval "$(docker-machine env default)"
> docker ps

### Building container
> docker-compose build

### Start locally
> docker-compose up web
> open "http://$(docker-machine ip default):8080"

Start shell
> docker-compose run shell

### Deploy to heroku
> heroku docker:release
