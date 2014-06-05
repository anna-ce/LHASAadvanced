#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Daily processing of all products
#
import os, argparse

force 	= 0
verbose = 0

def execute(cmd):
	if( force ):
		cmd += " -f"
		
	if(verbose):
		print cmd
		cmd += " -v"
	
	os.system(cmd)
	
def get_daily_precipitation():
	cmd = "./trmm_process.py "
	execute(cmd)

def get_daily_forecast():
	cmd = "./wrfqpe.py "
	execute(cmd)

def get_landslide_forecast():
	cmd = "./forecast_landslide_estimate.py"
	execute(cmd)

def get_flood_forecast():
	cmd = "./gfms_processing.py"
	execute(cmd)

def get_modis_floodmap():
	cmd = "./modis_floodmap.py"
	execute(cmd)

#
# ======================================================================
#
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='Landslide/Flood Processing')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new prodcuts to be re-generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose

	get_daily_precipitation()
	get_daily_forecast()
	get_flood_forecast()
	get_landslide_forecast()
	get_modis_floodmap()
	