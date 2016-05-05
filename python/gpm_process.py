#
# Processes TRMM Data for a specific region
#

import os, inspect, sys, math, urllib, glob, shutil
import argparse

import datetime
from datetime import date, timedelta
from dateutil.parser import parse
from osgeo import gdal
import numpy
import json
from ftplib import FTP
from browseimage import MakeBrowseImage, wms

import config

#from browseimage import MakeBrowseImage 
from s3 import CopyToS3
from level import CreateLevel

verbose 	= 0
force 		= 0
ftp_site 	= "jsimpson.pps.eosdis.nasa.gov"
path	 	= "pub/merged/3B42RT/"
gis_path 	= "NRTPUB/imerg/gis/"
	

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)

def get_daily_gpm_files(trmm_gis_files, mydir, year, month):
	filepath = gis_path+ "%02d" % ( month)
	
	if verbose:
		print "filepath", filepath
		print("Checking "+ftp_site+"/" + filepath + " for latest file...")
	
	try:
		ftp = FTP(ftp_site)
	
		ftp.login('pat@cappelaere.com','pat@cappelaere.com')               					# user anonymous, passwd anonymous@
		ftp.cwd(filepath)
	
	except Exception as e:
		print "FTP login Error", sys.exc_info()[0], e
		print "Exception", e
		sys.exit(-1)

	for f in trmm_gis_files:
		if verbose:
			print "Trying to download", f
		local_filename = os.path.join(mydir, f)
		if not os.path.exists(local_filename):
			if verbose:
				print "Downloading it...", f
			file = open(local_filename, 'wb')
			try:
				ftp.retrbinary("RETR " + f, file.write)
				file.close()
			except Exception as e:
				print "TRMM FTP Error", sys.exc_info()[0], e					
				os.remove(local_filename)
				ftp.close();
				sys.exit(-2)

	ftp.close()			
			
def process(gpm_dir, name, gis_file_day, ymd, regionName, region, s3_bucket, s3_folder ):
	
	# subset the file for that region
	bbox		= region['bbox']
	gis_file	= os.path.join(gpm_dir, gis_file_day)
	
	if not os.path.exists(gis_file):
		print "gis file does not exist", gis_file
		sys.exit(-1)
		
	region_dir	= os.path.join(gpm_dir,regionName)
	if not os.path.exists(region_dir):            
		os.makedirs(region_dir)
	
	subset_file	= os.path.join(region_dir, "%s.%s.tif" % (name,ymd))
	
	if force or not os.path.exists(subset_file):
		cmd = "gdalwarp -overwrite -q -te %f %f %f %f %s %s" % (bbox[0], bbox[1], bbox[2], bbox[3], gis_file, subset_file)
		execute(cmd)

	geojsonDir	= os.path.join(region_dir,"geojson")
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	levelsDir	= os.path.join(region_dir,"levels")
	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)

	merge_filename 		= os.path.join(geojsonDir, "%s.%s.geojson" % (name,ymd))
	topojson_filename 	= os.path.join(geojsonDir, "..", "%s.%s.topojson" % (name,ymd))
	browse_filename 	= os.path.join(geojsonDir, "..", "%s.%s_browse.tif" % (name,ymd))
	subset_filename 	= os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif" % (name,ymd))
	subset_aux_filename = os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif.aux" % (name,ymd))
	osm_bg_image		= os.path.join(geojsonDir, "..", "osm_bg.png")
	sw_osm_image		= os.path.join(geojsonDir, "..", "%s.%s_thn.jpg" % (name,ymd))

	levels 				= [377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3]
	
	# From http://colorbrewer2.org/
	hexColors 			= [ "#f7fcf0","#e0f3db","#ccebc5","#a8ddb5","#7bccc4","#4eb3d3","#2b8cbe","#0868ac","#084081","#810F7C","#4D004A" ]
	
	ds 					= gdal.Open( subset_file )
	band				= ds.GetRasterBand(1)
	data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
	
	geotransform 		= ds.GetGeoTransform()
	xorg				= geotransform[0]
	yorg  				= geotransform[3]
	pres				= geotransform[1]
	xmax				= xorg + geotransform[1]* ds.RasterXSize
	ymax				= yorg - geotransform[1]* ds.RasterYSize
	
	data /= 10			# back to mm
	
	if force or not os.path.exists(topojson_filename+".gz"):
		for l in levels:
			fileName 		= os.path.join(levelsDir, ymd+"_level_%d.tif"%l)
			CreateLevel(l, geojsonDir, fileName, ds, data, "precip", force, verbose)
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "precip_level_%d.geojson"%l)
			if os.path.exists(fileName):
				if verbose:
					print "merge", fileName
				with open(fileName) as data_file:    
					data = json.load(data_file)
		
				if 'features' in data:
					for f in data['features']:
						jsonDict['features'].append(f)
	

		with open(merge_filename, 'w') as outfile:
		    json.dump(jsonDict, outfile)	

		if verbose:
			output = " "
		else:
			output = " > /dev/null 2>&1"		

		# Convert to topojson
		cmd 	= "topojson -p -o "+ topojson_filename + " " + merge_filename + output
		execute(cmd)

		cmd 	= "gzip -f "+ topojson_filename
		execute(cmd)
		
	# problem is that we need to scale it or adjust the levels for coloring (easier)
	adjusted_levels 				= [3770, 2330, 1440, 890, 550, 340, 210, 130, 80, 50, 30]
	zoom = region['thn_zoom']
	
	if not os.path.exists(osm_bg_image):
		ullat = yorg
		ullon = xorg
		lrlat = ymax
		lrlon = xmax
		wms(ullat, ullon, lrlat, lrlon, osm_bg_image)
	
	if force or not os.path.exists(sw_osm_image):
		rColors 	= list(reversed(hexColors))
		MakeBrowseImage(ds, browse_filename, subset_filename, osm_bg_image, sw_osm_image, adjusted_levels, rColors, force, verbose, zoom)
		
	ds = None
	
	file_list = [ sw_osm_image, topojson_filename+".gz", subset_file ]
	
	CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
	
	if not verbose: # Cleanup
		cmd = "rm -rf %s %s %s %s %s %s" % ( osm_bg_image, browse_filename, subset_filename, subset_aux_filename, geojsonDir, levelsDir)
		execute(cmd)
	
def cleanupdir( mydir):
	print "cleaning up", mydir
	today 		= datetime.date.today()
	delta		= timedelta(days=config.DAYS_KEEP)
	dl			= today - delta
	lst 		= glob.glob(mydir+'/[0-9]*')

	for l in lst:
		basename = os.path.basename(l)
		if len(basename)==8:
			year 	= int(basename[0:4])
			month	= int(basename[4:6])
			day		= int(basename[6:8])
			dt		= datetime.date(year,month,day)
	
			if dt < dl:
				msg = "** delete "+l
				if verbose:
					print msg
				shutil.rmtree(l)

def cleanup():
	_dir			=  os.path.join(config.data_dir,"gpm")
	cleanupdir(_dir)
	
	

# ===============================
# Main
#
# python gpm_process.py --region d03 --date 2015-04-07 -v -f

if __name__ == '__main__':

	aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
	aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	assert(aws_access_key)
	assert(aws_secret_access_key)
	
	parser = argparse.ArgumentParser(description='Generate Daily Precipitation map')
	apg_input = parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose on/off")
	apg_input.add_argument("-d", "--date", help="Date 2015-03-20 or today if not defined")
	apg_input.add_argument("-r", "--region", help="Region")

	todaystr	= date.today().strftime("%Y-%m-%d")

	options 	= parser.parse_args()

	dt			= options.date or todaystr
	force		= options.force
	verbose		= options.verbose
	regionName	= options.region
	
	today		= parse(dt)
	year		= today.year
	month		= today.month
	day			= today.day
	doy			= today.strftime('%j')
	ymd 		= "%d%02d%02d" % (year, month, day)		

	gpm_dir	= os.path.join(config.data_dir, "gpm", ymd)
	if not os.path.exists(gpm_dir):
	    os.makedirs(gpm_dir)
	
	region		= config.regions[regionName]
	assert(region)
	
	s3_folder	= os.path.join("gpm", str(year), doy)
	s3_bucket	= region['bucket']
	
	gis_file_day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.1day.tif"%(year, month, day)
	gis_file_day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.1day.tfw"%(year, month, day)

	gis_file_3day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.3day.tif"%(year, month, day)
	gis_file_3day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.3day.tfw"%(year, month, day)

	gis_file_7day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.7day.tif"%(year, month, day)
	gis_file_7day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.7day.tfw"%(year, month, day)
	
	print gis_file_day
	files 				= [
		gis_file_day, gis_file_day_tfw, 
		gis_file_3day, gis_file_3day_tfw, 
		gis_file_7day, gis_file_7day_tfw
	]
	
	if force or not os.path.exists(os.path.join(gpm_dir,gis_file_day)):
		get_daily_gpm_files(files, gpm_dir, year, month)
		
	process(gpm_dir, "gpm_1d", gis_file_day, ymd, regionName, region, s3_bucket, s3_folder)
	process(gpm_dir, "gpm_3d", gis_file_day, ymd, regionName, region, s3_bucket, s3_folder)
	process(gpm_dir, "gpm_7d", gis_file_day, ymd, regionName, region, s3_bucket, s3_folder)
	
	cleanup()

