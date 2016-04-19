#
# forecastio generation of geojson data
#
import sys, os, inspect, urllib, urllib2, requests
import ssl
ssl.PROTOCOL_SSLv23 = ssl.PROTOCOL_TLSv1

import datetime
from datetime import date, timedelta
from dateutil.parser import parse
from pprint import pprint

# Site configuration
import config

import argparse
import json
import browseimage
from browseimage import mapbox_image
from s3 import CopyToS3

from PIL import Image, ImageDraw

force 	= 0
verbose = 0

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)

# ======================================================================
#	python forecastio.py --date 2016-04-15 --region d02 -v
#

if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='FORECAST.IO Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-r", "--region", 	help="Region")
	apg_input.add_argument("-d", "--date", 	help="Date", required=1)

	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	regionName	= options.region
	region		= config.regions[regionName]
	assert(region)
	
	basedir 	= os.path.dirname(os.path.realpath(sys.argv[0]))
	
	todaystr	= date.today().strftime("%Y-%m-%d")
	dt			= options.date or todaystr
	
	today		= parse(dt)
	tomorrow	= today + datetime.timedelta(hours=24)
	
	year		= today.year
	month		= today.month
	day			= today.day
	doy			= today.strftime('%j')
	ymd 		= "%d%02d%02d" % (year, month, day)		
	
	mydir		= os.path.join(config.data_dir,"forecastio", ymd, regionName)
	if not os.path.exists(mydir):            
		os.makedirs(mydir)
	
	s3_folder	= os.path.join("forecastio", str(year), doy)
	s3_bucket	= region['bucket']
	bbox		= region['bbox']
	zoom		= region['thn_zoom']
	
	APIKEY		= os.environ.get('FORECAST_API_KEY')
	baseurl		= "https://api.forecast.io/forecast/%s/" % APIKEY
	time		= dt+"T00:00:00Z"
	
	features	= []
	
	geojson_filename	= os.path.join(os.path.join(mydir,  "forecastio." + ymd + '.geojson'))
	geojsongz_filename	= os.path.join(os.path.join(mydir,  "forecastio." + ymd + '.geojson.gz'))
	osm_bg_image		= os.path.join(os.path.join(mydir,  "osm_bg_image.tif"))
	tif_filename		= os.path.join(os.path.join(mydir,  "forecastio." + ymd + '.tif'))
	thn_image			= os.path.join(os.path.join(mydir,  "forecastio." + ymd + '_thn.jpg'))

	#
	# Read GeoJSON File
	#
	units = 'us'
	
	if regionName == 'd02':
		with open('../rccp_coffeecrops2.geojson') as data_file:    
			data = json.load(data_file)

	if regionName == 'd05':
		units = 'si'
		with open('../rcmrd_teacrops2.geojson') as data_file:    
			data = json.load(data_file)

	#pprint(data)
	
	if force or not os.path.exists(geojson_filename):  
		for f in data['features'] :
			coordinates = f['geometry']['coordinates']
			longitude	= coordinates[0]
			latitude	= coordinates[1]
			
			name		= f['properties']['@id']
			
			if 'name' in f['properties']:
				name	= f['properties']['name']
			else:
				if 'add:city' in f['properties']:
					name = f['properties']['addr:city']
			
			url		= 	baseurl + "%f,%f,%s?exclude=[currently, hourly, flags]&units=%s" %( latitude,longitude, time, units ) 
	
			if verbose:
				print url
		
			response = requests.get(url)
			if response.status_code == 200:
				json_data 	= response.json()
				data		=  json_data['daily']['data'][0]
				
				if verbose:
					print data
		
				entry = {
					'type': 'Feature',
					'geometry': {
						'type': 'Point',
						'coordinates': [ longitude, latitude ]
					},
					"properties": {
						'dewPoint': 					data['dewPoint'],
						'apparentTemperatureMax':		data['apparentTemperatureMax'],
						'apparentTemperatureMaxTime': 	datetime.datetime.utcfromtimestamp(data['apparentTemperatureMaxTime']).isoformat()+'Z',
						'apparentTemperatureMin':		data['apparentTemperatureMin'],
						'apparentTemperatureMinTime': 	datetime.datetime.utcfromtimestamp(data['apparentTemperatureMinTime']).isoformat()+'Z',
						'humidity': 					data['humidity'],
						'name': 						name,
						'precipType':					data['precipType'],
						'precipIntensity':				data['precipIntensity'],
						'precipIntensityMax':			data['precipIntensityMax'],
						'pressure':						data['pressure'],
						'summary':						data['summary'],
						'temperatureMax': 				data['temperatureMax'],
						'temperatureMaxTime': 			datetime.datetime.utcfromtimestamp(data['temperatureMaxTime']).isoformat()+'Z',
						'temperatureMin': 				data['temperatureMin'],
						'temperatureMinTime': 			datetime.datetime.utcfromtimestamp(data['temperatureMinTime']).isoformat()+'Z',
						'windSpeed': 					data['windSpeed'],
						'windBearing': 					data['windBearing']
					}
				}
		
				features.append(entry)
		
		entries		= {
			'type': 'FeatureCollection',
			'features': features
		}

		with open(geojson_filename, 'w') as outfile:
			json.dump(entries, outfile)
		
		if force or not os.path.exists(geojsongz_filename):
			cmd = 'gzip < %s > %s' %( geojson_filename, geojsongz_filename)
			execute(cmd)
	
		
	if force or not os.path.isfile(thn_image):	
		centerlat 	= (bbox[1]+bbox[3])/2
		centerlon	= (bbox[0]+bbox[2])/2
		rasterXSize	= 400
		rasterYSize	= 250

		mapbox_image(centerlat, centerlon, zoom, rasterXSize, rasterYSize, osm_bg_image)

		ullon, ullat, lrlon, lrlat = browseimage.Gen_bbox(centerlat, centerlon, zoom, rasterXSize, rasterYSize)
		dx = (lrlon-ullon)/rasterXSize
		dy = (ullat-lrlat)/rasterXSize


		im 		= Image.open(osm_bg_image)
		draw 	= ImageDraw.Draw(im)

		for f in features :
			coordinates = f['geometry']['coordinates']
			lon		= coordinates[0]
			lat		= coordinates[1]
	
			x		= int((lon-ullon)/dx)
			y		= int((ullat-lat)/dx)
	
			draw.ellipse( [(x-1,y-1),(x+1,y+1)])

		im.save(tif_filename, "PNG")

		cmd = "cp %s %s" % (tif_filename, thn_image)
		execute(cmd)
	

	file_list = [ geojson_filename, geojsongz_filename, thn_image ]

	CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
	