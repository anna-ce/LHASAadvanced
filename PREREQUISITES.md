# OJO Bot

This is a prototype data processor/publisher for NASA. 

Maintained by [Pat Cappelaere](mailto:pat@cappelaere.com)
Vightel Corporation
pat@cappelaere.com

Developer Accounts Prerequisites
--------------------------------

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


Pre-Requisites
----------------

### Docker

Install docker on local machine anf get familiar with it
Download it from : https://www.docker.com/

### AWS Setup

Go to your Account  / Security Credentials
We need to create some IAM users and attach specific security policies

We will use CONVOX as our Platform as a Service (PaaS) provider to orchestrate and deploy services on AWS. (http://www.convox.com)

#### Create a CONVOX AWS IAM user

Follow instructions from here: http://convox.github.io/docs/creating-an-iam-user/

Make sure to download the credentials

#### Create an OJO Developer AWS IAM User

##### Create a Custom Policy
This policy will allow access to S3, SES and RDS services from the code

##### Create New Policy 

Policy Name: OJO

```shell
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*",
                "ses:*",
                "rds:*"
            ],
            "Resource": "*"
        }
    ]
}
```

##### Create OJO-BOT user

Under Permissions tab, attach OJO Policy you just created

Create Access Key and download it

#### SES (Simple Email Service)

To allow Publisher to send emails

Email Addresses tab

	Add verified send emails (sender email addresses)

SMTP Settings tab

	Create SMTP Credentials
	
You should see an ses-smtp-user in your IAM user list

### CONVOX PaaS setup

Get started with [CONVOX](https://console.convox.com)
[Docs here](https://convox.com/docs/)

Steps:

+  Create Account
+  Install New Rack
+  Install CONVOX CLI on your local machine

Log in on the CLI

> $ convox login console.convox.com --password xxxx-xxx-xx-xx-xxx

Switch to your rack

> $ convox switch personal/ojo-bot

Clone OJO-Publisher

> $ git clone git@github.com:vightel/ojo-bot.git

> $ cd ojo-bot
> $ convox apps create ojo-bot

Create PostgreDB

> $ convox services create postgres --name workshop_db
> $ convox services info workshop_db

Create [S3 Bucket](http://docs-staging.convox.com/docs/s3/)

> $ convox services create s3 --name workshop_bucket
> $ convox services info workshop_bucket

Create [Service Queue](http://docs-staging.convox.com/docs/sqs/)

> $ convox services create sqs --name workshop_queue
> $ convox services info workshop_queue

Create Lambda Functions for scheduling

Go to your AWS Management console Compute/Lambda
Create function to generate IMERG every 30mn (Set it to run every 30mn)
Note: Replace AWS_QUEUE by proper queue name

```python
import boto3, datetime
# Get the service resource
sqs = boto3.resource('sqs')

AWS_QUEUE="OJO-Q"

def send_msg():
    queue = sqs.get_queue_by_name(QueueName=AWS_QUEUE)
    response = queue.send_message(MessageBody='process_gpm_30mn')


def lambda_handler(event, context):
    print('Sending msg')
    try:
       send_msg()
    except:
        print('Send Message failed!')
        raise
    else:
        print('Done!')
        return 1
    finally:
        print('Complete at {}'.format(str(datetime.datetime.now())))
```

Create function to generate IMERG every 3hrs (set it to run every 3hrs)

```python
import boto3, datetime
# Get the service resource
sqs = boto3.resource('sqs')

AWS_QUEUE="OJO-Q"

def send_msg():
    queue = sqs.get_queue_by_name(QueueName=AWS_QUEUE)
    response = queue.send_message(MessageBody='process_gpm_3hrs')


def lambda_handler(event, context):
    print('Sending msg')
    try:
       send_msg()
    except:
        print('Send Message failed!')
        raise
    else:
        print('Done!')
        return 1
    finally:
        print('Complete at {}'.format(str(datetime.datetime.now())))
```


Create function to generate all products every day.  Set it to run once a day

```python
import boto3, datetime
# Get the service resource
sqs = boto3.resource('sqs')

AWS_QUEUE="OJO-Q"

def send_msg():
    queue = sqs.get_queue_by_name(QueueName=AWS_QUEUE)
    response = queue.send_message(MessageBody='process_all')


def lambda_handler(event, context):
    print('Sending msg to process all scripts')
    try:
       send_msg()
    except:
        print('Send Message failed!')
        raise
    else:
        print('Done!')
        return 1
    finally:
        print('Complete at {}'.format(str(datetime.datetime.now())))
```

## Set Environment

Set the environment variables in envs.docker.sh and your .bashrc or .tcshrc (if you want to develop on local machine)

> $ cp envs.docker.sh.tmpl envs.docker.sh
> $ vi .bashrc

## Configure Database
### Add extensions
Connect to database using [Navicat](https://www.navicat.com/)/phpAdmin/[psql](http://postgresguide.com/utilities/psql.html)

> env | grep DATABASE_URL_
> $ psql "dbname=d6or7541hmg7qi host=ec2-54-83-32-64.compute-1.amazonaws.com user=udeeblkngvmsh4 password=xxxxxxxxxxxxxxxxxxxxxxx port=6002 sslmode=require"

> d6or7541hmg7qi=> create extension postgis;
> d6or7541hmg7qi=> create extension fuzzystrmatch;
> d6or7541hmg7qi=> create extension postgis_tiger_geocoder;
> d6or7541hmg7qi=> create extension postgis_topology;

###Add required tables

Check /sql/public.sql and replace "udeeblkngvmsh4" with your own DATABASE OWNER as specified in your DATABASE_URL in ALTER TABLE statement

> d6or7541hmg7qi=> \i ./sql/public.sql
> d6or7541hmg7qi=> \q

### Customize Configuration Files
#### ./config/config.yaml
#### ./python/config.py

# Next Tuning Deployment
Enable SSH
> $ convox instances keyroll

Scale Up
> $ convox rack scale --type m3.large

> $ convox scale web --count 1 

> $ convox scale web --memory 512

> $ convox scale worker --count 1 

> $ convox scale worker --memory 512


Check
> $ convox apps info
> $ convox instances
