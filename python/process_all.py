#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Daily processing of all products
#
import sys, os, argparse
from datetime import date, timedelta
from subprocess import call
from smtplib import SMTP_SSL as SMTP  
from email.mime.text import MIMEText

try:
	from osgeo import osr, gdal
except:
	print "Error", sys.exc_info()[0]
	sys.exit(-1)
	
force 	= 0
verbose = 0
	
def emailErrorFile():
	try:
		# Read Error File
		textfile 	= "./errorlog.txt"
		fp 			= open(textfile, 'rb')
		msg 		= MIMEText(fp.read())
		fp.close()
		
		me			= os.environ['FASTMAIL_USER']
		password 	= os.environ['FASTMAIL_PASSWORD']
		smtp		= os.environ['FASTMAIL_SMTP']
		
		msg['Subject'] 	= 'Error processing daily landslide'
		msg['From'] 	= me
		msg['To'] 		= me
		print "sending error email to ", me
		# Send the message via our own SMTP server, but don't include the envelope header.
		s = SMTP(smtp)
		s.login(me, password)
		s.sendmail(me, [me], msg.as_string())
		s.quit()
	except Exception as e:
		print "exception sending email exception", e
		
def execute(cmd):
	if( force ):
		cmd += " -f"
	
	if(verbose):
		cmd += " -v"
		print cmd	
		
	err = call(cmd, shell=True)
	if err > 0:
		print "process_all execute err", err
		emailErrorFile()
	
def get_daily_forecast():
	cmd = "./wrfqpe.py "
	execute(cmd)

def process_script( str, dt ):
	cmd = "python ./%s --region d02 --date %s" % (str, dt)
	execute(cmd)

	cmd = "python ./%s --region d03 --date %s" % (str, dt)
	execute(cmd)

	cmd = "python ./%s --region d08 --date %s" % (str, dt)
	execute(cmd)
	
def process_global_script( str, dt ):
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
	cmd = "heroku pgbackups:capture --app ojo-streamer HEROKU_POSTGRESQL_COPPER_URL --expire"
	print cmd
	os.system(cmd)

def backup_ojo_wiki():
	cmd = "cd /Users/patricecappelaere/Development/ojo/ojo-wiki"
	print cmd
	os.system(cmd)

	cmd = "heroku pgbackups:capture --app ojo-wiki HEROKU_POSTGRESQL_ORANGE_URL --expire"
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
	
	try:
		me 			= sys.argv[0]
		mypath		= os.path.dirname(me) 
	
		print "Process All Path:",  sys.argv[0], mypath
		os.chdir(mypath)
	except:
		print "Unexpected error:", sys.exc_info()[0]
		sys.exit(-1)
	
	
	apg_input.add_argument("-f", "--force", action='store_true', help="Forces new products to be re-generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 		help="date")
	
	options 	= parser.parse_args()
	force		= options.force or force
	verbose		= options.verbose or verbose
	d			= options.date

	today		= date.today()
	dt			= d or today.strftime("%Y-%m-%d")
	
	yesterday	= today - timedelta(1)
	ydt			= yesterday.strftime("%Y-%m-%d")

	dayAfterYesterday	= today - timedelta(2)
	ydt2				= dayAfterYesterday.strftime("%Y-%m-%d")
		
	if 1:
		process_script('trmm_process.py', ydt)
		#get_daily_forecast()
		#get_flood_nowcast()
		
		process_script('landslide_nowcast.py', dt)
		#process_script('gpm_process.py', ydt)
		process_script('modis-active-fires.py', ydt)
		process_script('modis-burnedareas.py', ydt)
		process_script('quake.py', ydt)
		process_global_script('gfms_vectorizer.py', ydt)
		process_global_script('geos5.py', dt)
		process_global_script('gpm_global.py', ydt2)

		#process_script('viirs_CHLA.py', ydt)
		#process_script('chirps_prelim.py --period monthly', ydt)
		#process_script('chirps_prelim.py --period dekad', ydt)
		#process_script('chirps_prelim.py --period pentad', ydt)
		#process_script('vhi.py', ydt)
	
		#get_modis_floodmap()
		
		backup_ojo_streamer()
		backup_ojo_wiki()

	cleanup()
	