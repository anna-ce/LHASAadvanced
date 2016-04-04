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


#### S3 (Persistent Storage Service)

Create a CentroClima bucket (name as available)


#### RDS (Relational Database Service)

We will use CONVOX to create our PostgreSQL database

Get started with [CONVOX](https://convox.com/docs/getting-started/)

Steps:

+  Create Grid Account
+  Install New Rack
+  Install CONVOX CLI on your local machine
+  Log in on the CLI

Clone OJO-Publisher

> $ git clone git@github.com:vightel/ojo-bot.git

> $ cd ojo-bot
> $ convox apps create ojo-bot

Create PostgreDB

> $ convox services create postgres --name workshopdb

Set the environment

> $ convox services info workshopdb
Note: You will set DATABASE_URL env as provided URL.  See above

> $ cp envs.docker.sh.tmpl envs.docker.sh

Set all your environment variables


# NEXT.... NOT FINISHED
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
