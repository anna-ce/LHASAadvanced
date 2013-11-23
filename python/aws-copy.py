#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
import sys, os, inspect, math

# Amazon S3
import boto
import uuid

# Site configuration
import config
import argparse

force		= 0
verbose		= 0

#
# ======================================================================
#
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='MODIS Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force",   action='store_true', help="force it")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-l", "--file", nargs=1, help="file to copy")
	apg_input.add_argument("-b", "--bucket",  nargs=1, help="S3 bucket to copy it too")
	
	options 	= parser.parse_args()
	
	force		= options.force
	verbose		= options.verbose
	mbtiles		= options.file[0]
	bucket		= options.bucket[0]
	
	# copy mbtiles to S3
	if verbose:
		print "Copying "+ mbtiles+" to bucket:"+bucket
		
	conn 		= boto.connect_s3()

	mybucket 	= conn.get_bucket(bucket)
	fname		= os.path.basename(mbtiles)
	 
	if verbose:
		print "storing to s3:", bucket, fname

	from boto.s3.key import Key
	k 			= Key(mybucket)
	k.key 		= fname
	k.set_contents_from_filename(mbtiles)
	mybucket.set_acl('public-read', fname )