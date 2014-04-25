# OJO Bot

This is a prototype for NASA. 

Pat Cappelaere	Vightel		pat@cappelaere.com

## Requirements & Installation

Node.js

## Database Operations
# Dump local database
This application uses the same database as OJO-Streamer.
Make sure to point to proper db using environment variable

NOTE:
// to reset database and reload
> heroku pg:reset DATABASE


## Set HEROKU Env	
> heroku config:set DATABASE=
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
