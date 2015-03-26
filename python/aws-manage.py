#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
import sys, os, inspect, math

# Amazon S3
import boto
import uuid
import os, datetime, glob, shutil
from boto.s3.connection import S3Connection
from datetime import timedelta

# Site configuration
import config
import argparse

force		= 0
verbose		= 0

buckets = ["ojo-d2", "ojo-d3"]

dirs2	= ["trmm"]

dirs	= [	"ant_r/d02",
			"ant_r/d03",
			"landslide_nowcast/d02",
			"landslide_nowcast/d03",
			"trmm",
			"trmm/3B42RT",
			"trmm/d02",
			"trmm/d03"
		]
	
def manage_buckets(conn, dl):
	for b in buckets:
		print "** bucket:", b
		bucket 		= conn.get_bucket(b)
		rs 			= bucket.list()
		keysList 	= []

		for key in rs:
			dt 		= boto.utils.parse_ts(key.last_modified)
			msg 	= ""
			name	= key.name
			dirname	= os.path.dirname(name)
			if (len(dirname)==8) and (dt.date() < dl):
				msg = "** delete **"
				print b, name, key.size, dt, msg
				keysList.append(key)
			
		result = bucket.delete_keys([key.name for key in keysList])
			
def manage_folder(f, dl):
	basename = os.path.basename(f)
	if len(basename)==8:
		year 	= int(basename[0:4])
		month	= int(basename[4:6])
		day		= int(basename[6:8])
		dt		= datetime.date(year,month,day)
		
		msg = ""
		if dt < dl:
			msg = "** delete "+f
			print basename, year, month, day, msg
			shutil.rmtree(f)
		
def manage_local_dirs(dl, data_dir):
	for d in buckets:
		folder 	= os.path.join(data_dir, d)
		print folder
		lst 	= glob.glob(folder+'/[0-9]*')
		for l in lst:
			manage_folder(l, dl)
		
#
# ======================================================================
# Only keep AWS keys in buckets that are less than 90 days old
#
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='AWS Mange')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force",   action='store_true', help="force it")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	
	force		= options.force
	verbose		= options.verbose
			
	aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
	aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	
	conn 	= S3Connection(aws_access_key, aws_secret_access_key)
	
	today 	= datetime.date.today()
	delta	= timedelta(days=90)
	dl		= today - delta
	
	manage_buckets(conn, dl)
	manage_local_dirs(dl, config.data_dir )
	#manage_local_dirs(dl, "/Users/patricecappelaere/Development/ojo/ojo-bot/tmp")
	