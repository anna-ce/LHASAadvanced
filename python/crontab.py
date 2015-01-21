#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# This is the file to be run every day at 8:00AM Easter time
#

import sys, os, inspect, glob
import datetime
from pytz import timezone
from datetime import date, timedelta	#,timezone
import dateutil.parser
import argparse
import config

from boto.s3.connection import S3Connection

regions		= ['d02', 'd03']
buckets 	= ['ojo-d2', 'ojo-d3']
products	= ['trmm_24', 'wrf_24', 'gmfs_24', "MODIS", "landslide_nowcast", "mcd45"]
force		= 0
verbose		= 0
today 		= date.today()
d100		= datetime.timedelta(days=90)

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)
	
def older_than_sixty_days(last_modified):
	full_dt = dateutil.parser.parse(last_modified)
	fdate	= datetime.date(full_dt.year,full_dt.month,full_dt.day )
	delta	= (today - fdate) - d100
	if fdate < today - d100 :
		return 1
	else:
		return 0
	
def removed_sixty_days_old_files_from_s3_bucket(conn, bucket):
	if verbose:
		print "removed_sixty_days_old_files_from_s3_bucket...", bucket
		
	mybucket 	= conn.get_bucket(bucket)
	lst 		= mybucket.list()
	
	delete_key_list = []
	for key in lst:
		if older_than_sixty_days(key.last_modified ):
			for p in products:
				if p in key.name:
					print "delete ", key.name, key.last_modified
					delete_key_list.append(key)

	if len(delete_key_list) > 0:
	    bucket.delete_keys(delete_key_list)
						
def removed_old_files_from_s3():
	aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
	aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	
	conn = S3Connection(aws_access_key, aws_secret_access_key)
	removed_sixty_days_old_files_from_s3_bucket(conn, 'ojo-d3')
	removed_sixty_days_old_files_from_s3_bucket(conn, 'ojo-d2')

def removed_old_folders(subfolder):
	if verbose:
		print "removed_old_folders", subfolder
	
	found_folders = glob.glob(subfolder)
	for found in found_folders:
		arr = found.split('/')
		ymd = arr.pop()
		
		# check if it is a YYYMMDD format
		if len(ymd) == 8:
			yyyy 	=  ymd[0:4]
			mm		=  ymd[4:6]
			dd		=  ymd[6:8]
			
			#dt		= datetime.date(yyyy, mm, dd )
			
			if older_than_sixty_days(yyyy+"-"+mm+"-"+dd):
				print "** OLDER", ymd, yyyy, mm, dd
				cmd = "rm -rf " + found
				execute(cmd)
			#else:
			#	print ymd
		#else:
		#	print len(ymd), ymd
		
def removed_old_files_from_local_storage():
	#folders = ['trmm','landslide_nowcast','ant_r']
	folders = ['landslide_nowcast', 'trmm', 'ant_r', 'wrf']
	for f in folders:
		d 		= os.path.join(config.data_dir, f, "*")
		removed_old_folders(d)
		
		for r in regions:
			d 		= os.path.join(config.data_dir, f, r+"/*")
			removed_old_folders(d)
			
			
def generate_landslide_nowcast():
	ymd 	= "%d%02d%02d" % (today.year, today.month, today.day)
	cmd 	= "landslide_nowcast.py -v --region d02 --date "+ ymd
	if verbose:
		cmd += " -v"
		
	execute(cmd)

	cmd = "landslide_nowcast.py -v --region d03 --date "+ ymd
	if verbose:
		cmd += " -v"
		
	execute(cmd)
	
def	backup_ojo_wiki_db():
	if verbose:
		print "backup_ojo_wiki_db..."
		
	cmd = "cd ~/Development/ojo/ojo-wiki"
	execute(cmd)
	cmd = "heroku pgbackups:capture --app ojo-wiki --expire"
	execute(cmd)
	
def backup_ojo_streamer_db():
	if verbose:
		print "backup_ojo_streamer_db..."
	cmd = "cd ~/Development/ojo/ojo-streamer"
	execute(cmd)
	cmd = "heroku pgbackups:capture --app ojo-streamer --expire"
	execute(cmd)
	
def restart_ojo_streamer():
	cmd = "cd ~/Development/ojo/ojo-streamer"
	execute(cmd)
	cmd = "heroku restart --app ojo-streamer"
	execute(cmd)
	
# =======================================================================
# Main
#
if __name__ == '__main__':

	parser 		= argparse.ArgumentParser(description='Generate Forecast Landslide Estimates')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", 	action='store_true', help="Forces new products to be generated")
	apg_input.add_argument("-v", "--verbose", 	action='store_true', help="Verbose Flag")

	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	removed_old_files_from_local_storage()
	
	#removed__old_files_from_s3()
	#generate_landslide_nowcast()
	
	#backup_ojo_wiki_db()
	#backup_ojo_streamer_db()
	
	#restart_ojo_streamer()