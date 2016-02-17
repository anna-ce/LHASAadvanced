#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# GPM Daily processing of all products
#	Run daily at 8:00AM
#
import sys, os, argparse, logging
from datetime import date, timedelta
from subprocess import call
from smtplib import SMTP_SSL as SMTP  
from email.mime.text import MIMEText

try:
	from osgeo import osr, gdal
except:
	print "Error", sys.exc_info()[0]
	sys.exit(-1)
	
force 	= 1
verbose = 0

def emailFile( textfile, subject):
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
		textfile 	= "./errorlog.txt"
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
	if err > 0:
		logger.error("execute err %s", err)
		emailErrorFile()
	
def process_script( str, dt, regions ):	
	for r in regions :
		cmd = "cat /dev/null > errorlog.txt"
		os.system(cmd)
		
		cmd = "python ./%s --region %s --date %s" % (str, r, dt)
		execute(cmd)
	
def process_global_script( str, dt ):
	cmd = "cat /dev/null > errorlog.txt"
	os.system(cmd)
	
	cmd = "python ./%s --date %s" % (str, dt)
	execute(cmd)
	
def cleanup():
	cmd = "python aws-manage.py"
	execute(cmd)
	
#
# ======================================================================
#
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='GPM daily Processing')
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
		
			
	process_global_script('gfms_vectorizer.py', ydt)
	process_global_script('gpm_global.py', ydt)
		
	# Do Landlside Nowcast here
	
	cleanup()
	emailFile( logfile, "Success GPM daily products!" )
	