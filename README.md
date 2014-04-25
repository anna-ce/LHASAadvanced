# OJO Streamer

This is a prototype for NASA. 

## Requirements & Installation

Node.js
Postgresql

## Database Operations
# Dump local database
// check db_dump.sh
// command to dump
then upload to S3 and make public
then import to heroku
heroku restart


# upload to https://console.aws.amazon.com/s3/home?region=us-west-2
# make it public
# get public url

# restore heroku database
> heroku pgbackups:restore DATABASE 'https://s3.amazonaws.com/ojo-databases/dk.dump'
> git push heroku master

NOTE:
// to reset database and reload
> heroku pg:reset DATABASE
> heroku pgbackups:restore DATABASE 'https://s3.amazonaws.com/ojo-databases/dk.dump'

Pat Cappelaere	Vightel		pat@cappelaere.com

## Set HEROKU Env	
> heroku config:set AWS_ACCESSKEYID=
> heroku config:set AWS_SECRETACCESSKEY=
> heroku config:set AWS_REGION=

## And start
>git push heroku master
>heroku logs --tail --ps postgres --app ojo-streamer
	
## Facebook Testing / Tunneling
> ngrok 7464
	This will display the current status of the tunnel and a public URL To use for testing
	You will have to change the Facebook App Setting Website Site URL to point to proper URL
