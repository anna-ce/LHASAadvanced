#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Daily processing of all products
#

import sys, os, argparse, logging
from datetime import date, timedelta
from subprocess import call
from smtplib import SMTP_SSL as SMTP  
from email.mime.text import MIMEText

from osgeo import osr, gdal
import config
	
force 		= 1
verbose 	= 0

ERRLOG_FILE = "./errorlog.txt"

def emailFile( textfile, subject):
	if not config.SEND_EMAIL:
		return
		
	try:
		fp 			= open(textfile, 'rb')
		msg 		= MIMEText(fp.read())
		fp.close()
		
		me			= os.environ['FASTMAIL_USER']
		password 	= os.environ['FASTMAIL_PASSWORD']
		smtp		= os.environ['FASTMAIL_SMTP']
		
		msg['Subject'] 	= subject
		msg['From'] 	= me
		msg['To'] 		= me
		if verbose:
			print "sending email to ", me
		# Send the message via our own SMTP server, but don't include the envelope header.
		s = SMTP(smtp)
		s.login(me, password)
		s.sendmail(me, [me], msg.as_string())
		s.quit()
	except Exception as e:
		print "exception sending email exception", e
		
def emailErrorFile():
		textfile 	= ERRLOG_FILE
		subject		= "Error processing daily scripts"
		emailFile( textfile, subject)
		
def execute(cmd):
	if( force ):
		cmd += " -f"
	
	if(verbose):
		cmd += " -v"
		print cmd	
	
	logger.info(cmd)
		
	err = call(cmd, shell=True)
	if err < 0:
		logger.error("execute err %s", err)
		emailErrorFile()
	
def get_daily_forecast():
	cmd = "./wrfqpe.py "
	execute(cmd)

def process_script( str, dt, regions ):	
	for r in regions :
		cmd = "cat /dev/null > " + ERRLOG_FILE
		os.system(cmd)
		
		cmd = "python ./%s --region %s --date %s" % (str, r, dt)
		execute(cmd)
	
def process_global_script( str, dt ):
	cmd = "cat /dev/null > " + ERRLOG_FILE
	os.system(cmd)
	
	cmd = "python ./%s --date %s" % (str, dt)
	execute(cmd)

def get_flood_nowcast():
	cmd = "./gfms_processing.py"
	execute(cmd)

def get_modis_floodmap():
	cmd = "./modis_floodmap.py"
	execute(cmd)

def restart_ojo_streamer():
	cmd = "cd /Users/patricecappelaere/Development/ojo/ojo-streamer"
	print cmd
	os.system(cmd)
	
	cmd = "heroku restart --app ojo-streamer"
	print cmd
	os.system(cmd)

def backup_ojo_streamer():
	cmd = "heroku pg:backups capture --app ojo-streamer HEROKU_POSTGRESQL_COPPER_URL "
	print cmd
	os.system(cmd)

def backup_ojo_wiki():
	cmd = "cd /Users/patricecappelaere/Development/ojo/ojo-wiki"
	print cmd
	os.system(cmd)

	cmd = "heroku pg:backups capture --app ojo-wiki HEROKU_POSTGRESQL_ORANGE_URL "
	print cmd
	os.system(cmd)
	
def cleanup():
	cmd = "python aws-manage.py"
	execute(cmd)
	
#
# ======================================================================
#
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='Landslide/Flood Processing')
	apg_input 	= parser.add_argument_group('Input')
	
	logfile		= "./process.log"
	os.system("rm -f "+logfile)
	
	logging.basicConfig(filename = "./process.log", level=logging.INFO, format='%(asctime)s %(message)s')
	logger 		= logging.getLogger();
	
	try:
		me 			= sys.argv[0]
		mypath		= os.path.dirname(me) 
	
		print "Process All Path:",  sys.argv[0], mypath
		if mypath:
			os.chdir(mypath)
	except:
		print "Unexpected error:", sys.exc_info()[0]
		sys.exit(-1)
	
	apg_input.add_argument("-f", "--force", 	action='store_true', help="Forces new products to be re-generated")
	apg_input.add_argument("-v", "--verbose", 	action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 		help="date")
	
	options 				= parser.parse_args()
	force					= options.force or force
	verbose					= options.verbose or verbose
	d						= options.date

	today					= date.today()
	dt						= d or today.strftime("%Y-%m-%d")
	
	if d == None:		# Date has not been specified, it is today
		yesterday			= today - timedelta(1)
		ydt					= yesterday.strftime("%Y-%m-%d")

		dayAfterYesterday	= today - timedelta(2)
		ydt2				= dayAfterYesterday.strftime("%Y-%m-%d")
		
	else:				# We want to run for that specific date
		ydt					= dt
		ydt2				= dt
		
	print "Processing date:", dt, ydt, ydt2
		
	regions 				= ["d02", "d03", "d08", "d09", "d10"]
	regions2 				= ["d02", "d03", "d08", "d09", "d10"]
	
	if 1:
		process_script('trmm_process.py', 		ydt, regions2)

		# GPM regional products
		# process_script('gpm_process.py ', 		ydt2, regions2)				

		# Global GPM products
		#process_global_script('gpm_global.py --timespan 1day', 		ydt2)		
		#process_global_script('gpm_global.py --timespan 3day', 		ydt2)		
		#process_global_script('gpm_global.py --timespan 7day', 		ydt2)		
		
		cmd = "python gpm_daily.py --regions 'global,d02,d03,d08,d09,d10,r01,r02,r03,r04,r05,r06,r07,r08,r09,r10' --date " + ydt
		execute(cmd)
		
		process_script('landslide_nowcast.py', 	dt, regions)
		process_script('modis-active-fires.py', ydt, regions2)
		process_script('viirs-active-fires.py', ydt, regions2)
		
		# broken for 2016
		#process_script('modis-burnedareas.py', 	ydt, regions2)
		
		process_script('quake.py', 				ydt, regions2)
		
		process_global_script('gfms_vectorizer.py', ydt)
		
		process_global_script('landslide_nowcast_global.py', dt)
		#process_global_script('geos5.py', dt)

		#process_script('viirs_CHLA.py', ydt, regions2)
		
		#process_script('chirps_prelim.py --period monthly', ydt)
		#process_script('chirps_prelim.py --period dekad', ydt)
		#process_script('chirps_prelim.py --period pentad', ydt)
		#process_script('vhi.py', ydt)
	
		#get_modis_floodmap()
		
		backup_ojo_streamer()
		backup_ojo_wiki()

	cleanup()
	emailFile( logfile, "Success processing python scripts!" )
	