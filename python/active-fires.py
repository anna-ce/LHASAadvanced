#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
# Access and Process MODIS Active Fires
#
# https://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_7d.csv
# http://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_48h.csv
# http://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_24h.csv
#

import numpy, sys, os, inspect, io
import urllib
import csv
import json

# Site configuration
import config
import argparse

active_fires_urls = [
	{ 	"url": "https://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_7d.csv",
		"csv": "Central_America_7d.csv",
		"geojson": "Central_America_7d.geojson"
	},
	{ 	"url": "https://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_48h.csv",
		"csv": "Central_America_48h.csv",
		"geojson": "Central_America_48h.geojson"
	},
	{ 	"url": "https://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_24h.csv",
		"csv": "Central_America_24h.csv",
		"geojson": "Central_America_24h.geojson"
	}
]

def csv_to_geojson(csv_filename, geojson_filename):
	f 		= open( csv_filename, 'r' )
	reader 	= csv.DictReader( f, fieldnames = ( 'latitude','longitude','brightness','scan','track','acq_date','acq_time','satellite','confidence','version','bright_t31','frp' ) )
	
	features = []
	index 	 = 0
	for row in reader:
		# skip first row
		if index > 0:
			dt 	= row['acq_time']
			sat = row['satellite']
			if sat == 'T':
				sat = 'Terra'
			if sat == 'A':
				sat = 'Aqua'
			properties = {
				'brightness': row['brightness'],
				'acq_date': row['acq_date']+"T"+dt[1:3]+":"+dt[3:]+"Z",
				'satellite': sat,
				'confidence': row['confidence']
			}
			latitude 	= float(row['latitude']) 
			longitude 	= float(row['longitude'])
			coordinates = [longitude, latitude]
			feature = {"type": "Feature", "geometry": { "type": "Point", "coordinates": coordinates}, "properties": properties}
			features.append(feature)
		index += 1
			
	geojson = {"type": "FeatureCollection", "features": features}
	
	with io.open(geojson_filename, 'w', encoding='utf-8') as f:
		f.write(unicode(json.dumps(geojson, ensure_ascii=False)))
		
	print "Done:", geojson_filename
	
def process_url( f ):
	csv_filename		= os.path.join(config.data_dir, "modis_fires", f['csv'])
	geojson_filename	= os.path.join(config.data_dir, "modis_fires", f['geojson'])
	
	if not os.path.exists(csv_filename):
		urllib.urlretrieve(f['url'], csv_filename)
		
	if not os.path.exists(geojson_filename):
		csv_to_geojson(csv_filename, geojson_filename)
		
	cmd = "./aws-copy.py --bucket ojo-global --file " + geojson_filename
	if verbose:
		cmd += " --verbose "
		print cmd
	os.system(cmd)
#
# ======================================================================
#
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='MODIS Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	
	# get last 7 days
	url_7day 	= "https://firms.modaps.eosdis.nasa.gov/active_fire/text/Central_America_7d.csv"
	filename	= os.path.join(config.data_dir, "modis_fires", "Central_America_7d.csv")

	for f in active_fires_urls:
		process_url(f)