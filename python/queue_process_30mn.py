#
# This is called by cron.  It is used to queue a message to be picked by TBD workers
#

import boto3, datetime
# Get the service resource
sqs = boto3.resource('sqs', region_name='us-east-1')

AWS_QUEUE	= "OJO-Q"
MSG_REQUEST	= "process_30mn" 

try:
	queue 		= sqs.get_queue_by_name(QueueName= AWS_QUEUE)
	response 	= queue.send_message(MessageBody= MSG_REQUEST)
	print "Queued ", MSG_REQUEST, datetime.datetime.now()
except:
	print "Send Message failed", MSG_REQUEST, datetime.datetime.now()
