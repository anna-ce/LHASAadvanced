#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
# Access and Process USGS Earthquakes
#
#

import numpy, sys, os, inspect, io
import urllib
import csv
import json

# Site configuration
import config
import argparse


force 	= 0
verbose = 0

quakes_urls = [
	{ 	"url": "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
		"geojson": "quakes_2.5_day.geojson"
	},
	{ 	"url": "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson",
		"geojson": "quakes_2.5_week.geojson"
	},
	{ 	"url": "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson",
		"geojson": "quakes_2.5_month.geojson"
	}
]

def process_url( f ):
	geojson_filename	= os.path.join(config.data_dir, "quakes", f['geojson'])
	
	if force or not os.path.exists(geojson_filename):
		if verbose:
			print "retrieving:", geojson_filename
		urllib.urlretrieve(f['url'], geojson_filename)

	cmd = "./aws-copy.py --bucket ojo-global --file " + geojson_filename
	if verbose:
		cmd += " --verbose "
		print cmd
	os.system(cmd)
#
# ======================================================================
#
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='USGS Quake Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	
	for f in quakes_urls:
		process_url(f)