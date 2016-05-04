import os.path

import boto
from boto.s3.connection import S3Connection

aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	
conn = S3Connection(aws_access_key, aws_secret_access_key)

#conn = S3Connection()

nasaNexBucket = conn.get_bucket("nasanex")

#keys = nasaNexBucket.list("Landsat/gls/2000/001")
#keys = nasaNexBucket.list("MODIS/MOLA/MYD13Q1.005")
#keys = nasaNexBucket.list("NEX-DCP30")
keys = nasaNexBucket.list("NEX-GDDP")

for key in keys:
    print(key)