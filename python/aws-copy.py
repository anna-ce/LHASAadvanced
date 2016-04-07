#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
import sys, os, inspect, math

# Amazon S3
import boto
import uuid
import os, shutil
from boto.s3.connection import S3Connection

# Site configuration
import config
import argparse

force		= 0
verbose		= 0

#
# ======================================================================
#
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='AWS Copy')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force",   action='store_true', help="force it")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-l", "--file", 	  nargs=1, help="file to copy")
	apg_input.add_argument("-b", "--bucket",  nargs=1, help="S3 bucket to copy it too")
	apg_input.add_argument("-s", "--folder",  nargs=1, help="S3 subfolder to copy it too")
	
	options 	= parser.parse_args()
	
	force		= options.force
	verbose		= options.verbose
	fileName	= options.file[0]
	bucket		= options.bucket[0]
			
	if config.USING_AWS_S3_FOR_STORAGE:
		aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
		aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	
		conn = S3Connection(aws_access_key, aws_secret_access_key)
	
		#conn 		= boto.connect_s3()

		mybucket 	= conn.get_bucket(bucket)
		fname		= os.path.basename(fileName)
	 

		from boto.s3.key import Key
		k 			= Key(mybucket)
	
		if options.folder:
			k.key = options.folder[0] + "/" + fname
		else:
			k.key = fname

		# Check if it already exists
		possible_key = mybucket.get_key(k.key)
	
		if force or not possible_key:
			if verbose:
				print "storing to s3:", bucket, k.key
	
			k.set_contents_from_filename(fileName)
			mybucket.set_acl('public-read', k.key )
			
	if config.USING_LOCAL_DIR_FOR_STORAGE:
		if options.folder:
			dest_dir = os.path.join(config.LOCAL_DIR_STORAGE, bucket, options.folder)
		else:
			dest_dir = os.path.join(config.LOCAL_DIR_STORAGE, bucket)
			
		if( not os.path.exists(dest_dir)):
			if verbose:
				print "Making dest dir", dest_dir
			os.makedirs(dest_dir)			
			
		fname	= os.path.basename(fileName)
			
		dest_file_name = os.path.join(dest_dir, fname)
		if verbose:
			print "Copying ", f, " to ", dest_file_name
	
		shutil.copy(f, dest_file_name)	