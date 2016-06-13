#!/usr/bin/env python
#
# GEOS-5 Daily Precipitation Forecast Product
#
# http://gmao.gsfc.nasa.gov/products/documents/GEOS_5_FP_File_Specification_ON4v1_0.pdf

import numpy, sys, os, inspect, glob, shutil
from osgeo import osr, gdal
from ftplib import FTP
import datetime

import datetime
from datetime import date, timedelta
from dateutil.parser import parse

import warnings
from gzip import GzipFile
import numpy
import json

import urllib2
import multiprocessing

# Site configuration
import config
import argparse

from browseimage import MakeBrowseImage, wms
from s3 import CopyToS3
from level import CreateLevel

verbose 	= 0
force 		= 0
processes	= 4 #multiprocessing.cpu_count()

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)

def multiprocessing_download(filepath, local_filename):
	if verbose:
		print "multiprocessing_download ", filepath, local_filename

	try:
		ftp_site 	= "ftp.nccs.nasa.gov"
		ftp 		= FTP(ftp_site)

		ftp.login('gmao_ops','')
		ftp.cwd(filepath)
	
		f 			= os.path.basename(local_filename)
		if not os.path.exists(local_filename):
			print "Trying to Download...", f
			file = open(local_filename, 'wb')
			try:
				ftp.retrbinary("RETR " + f, file.write)
				file.close()
			except Exception as e:
				print "GEOS5 FTP Error", filepath, filename, sys.exc_info()[0], e					
				os.remove(local_filename)
				ftp.close();
				sys.exit(-2)
		else:
			if verbose:
				print "file exists", local_filename
				
	except Exception as e:
		print "multiprocessing exception:", sys.exc_info()[0], e
		
def get_files(year, mydir, files):
	pool 		= multiprocessing.Pool(processes=processes)
	mstr		= "%02d" % month
	dstr		= "%02d" % day

	ftp_site 		= "ftp.nccs.nasa.gov"
	filepath 		= "fp/forecast/Y%s/M%s/D%s/H00" % (year, mstr, dstr)		
	local_filenames = map(lambda x: os.path.join(mydir, x), files)
	
	for f in local_filenames:
		pool.apply_async(multiprocessing_download, args=(filepath, f, ))
	
	pool.close()
	pool.join()
	
def get_files_old(year, mydir, files):
	# ftp://ftp.nccs.nasa.gov/fp/forecast/Y2015/M08/D10/H00/

	mstr		= "%02d" % month
	dstr		= "%02d" % day

	ftp_site 	= "ftp.nccs.nasa.gov"
	path 		= "fp/forecast/Y%s/M%s/D%s/H00" % (year, mstr, dstr)		
	if verbose:
		print "get_files", ftp_site, path
	
	ftp = FTP(ftp_site)

	ftp.login('gmao_ops','')
	ftp.cwd(path)

	for f in files:
		filename = f
		if verbose:
			print "Trying to download", filename
		local_filename = os.path.join(mydir, filename)
		if not os.path.exists(local_filename):
			if verbose:
				print "Downloading it...", local_filename
			file = open(local_filename, 'wb')
			try:
				ftp.retrbinary("RETR " + filename, file.write)
				file.close()
			except Exception as e:
				print "TRMM FTP Error", sys.exc_info()[0], e					
				os.remove(local_filename)
				ftp.close();
				sys.exit(-2)

	ftp.close()
		
def process_file( mydir, filename, s3_bucket, s3_folder):
	print "Processing", filename
	
	geojsonDir	= os.path.join(mydir,"geojson")
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	levelsDir	= os.path.join(mydir,"levels")
	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)

	#shpDir	= os.path.join(mydir,"shp")
	#if not os.path.exists(shpDir):            
	#	os.makedirs(shpDir)

	super_subset_file	= os.path.join(mydir, "geos5_precip_super.%s.tif" % ymd)
	merge_filename 		= os.path.join(geojsonDir, "geos5_precip.%s.geojson" % ymd)
	topojson_filename 	= os.path.join(geojsonDir, "..", "geos5_precip.%s.topojson" % ymd)
	browse_filename 	= os.path.join(geojsonDir, "..", "geos5_precip.%s_browse.tif" % ymd)
	subset_filename 	= os.path.join(geojsonDir, "..", "geos5_precip.%s_small_browse.tif" % ymd)
	subset_aux_filename	= os.path.join(geojsonDir, "..", "geos5_precip.%s_small_browse.tif.aux.xml" % ymd)
	osm_bg_image		= os.path.join(mydir, "../..", "osm_bg.png")
	sw_osm_image		= os.path.join(geojsonDir, "..", "geos5_precip.%s_thn.jpg" % ymd)
	json_filename		= os.path.join(geojsonDir, "geos5_precip.%s.json" % (ymd))
	#shp_filename 		= os.path.join(mydir, "geos5_precip.%s.shp.gz" % (ymd))
	#shp_zip_file		= os.path.join(mydir, "geos5_precip.%s.shp.zip" % (ymd))
	
	#if force or not os.path.exists(subset_file):
	#	cmd = "gdalwarp -overwrite -q -te %f %f %f %f %s %s" % (bbox[0], bbox[1], bbox[2], bbox[3], filename, subset_file)
	#	execute(cmd)
	
	ds 					= gdal.Open( filename )
	geotransform		= ds.GetGeoTransform()
	px					= geotransform[1] / 2
	py					= geotransform[5] / 2
	
	xorg				= geotransform[0]
	yorg  				= geotransform[3]

	xmax				= xorg + geotransform[1]* ds.RasterXSize
	ymax				= yorg + geotransform[5]* ds.RasterYSize
	
	#print ymax, xorg, yorg, xmax
	
	ds					= None

	# upsample and convolve
	if force or not os.path.exists(super_subset_file):
		# we need to have square pixels
		cmd = "gdalwarp -overwrite -q -r cubicspline -tr %s %s  -co COMPRESS=LZW %s %s" % (str(px), str(px), filename, super_subset_file)
		execute(cmd)
	
	levels 				= [377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3]

	# http://hclwizard.org/hcl-color-scheme/
	# http://vis4.net/blog/posts/avoid-equidistant-hsv-colors/
	# from http://tristen.ca/hcl-picker/#/hlc/12/1/241824/55FEFF
	
	# This is in inverse order from levels
	#hexColors 			= [ "#56F6FC","#58DEEE","#5BC6DE","#5EAFCC","#5E99B8","#5D84A3","#596F8D","#535B77","#4A4861","#3F374B","#322737","#241824"]
	
	# GPM palette
	hexColors 			= [ "#f7fcf0","#e0f3db","#ccebc5","#a8ddb5","#7bccc4","#4eb3d3","#2b8cbe","#0868ac","#084081","#810F7C","#4D004A" ]
	
	ds 					= gdal.Open( super_subset_file )
	band				= ds.GetRasterBand(1)
	data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
	
	if force or not os.path.exists(topojson_filename+".gz"):
		for l in levels:
			fileName 		= os.path.join(levelsDir, ymd+"_level_%d.tif"%l)
			CreateLevel(l, geojsonDir, fileName, ds, data, "geos5_precip", force, verbose)
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "geos5_precip_level_%d.geojson"%l)
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

		# Convert to topojson
		quiet = "> /dev/null 2>&1"
		if verbose:
			quiet = " "
			
		cmd 	= "topojson -p --bbox --simplify-proportion 0.5 -o "+ topojson_filename + " " + merge_filename + quiet
		execute(cmd)

		cmd 	= "gzip -f "+ topojson_filename
			
		execute(cmd)
	
	# Create shapefile gz
	#if force or not os.path.exists(shp_filename):
	#	# Convert simplified topojson to geojson
	#	cmd = "topojson-geojson --precision 4 %s -o %s" % (topojson_filename, geojsonDir)
	#	execute(cmd)
		
	#	cmd = "ogr2ogr -f 'ESRI Shapefile' %s %s" % (shpDir, json_filename)
	#	execute(cmd)
		
		#cmd = "cd %s; tar -zcvf %s %s" % (mydir, shp_filename, shpDir)
	#	cmd 	= "cd %s; zip %s shp/*" %(mydir, shp_zip_file)
		
	#	execute(cmd)
		
	if not os.path.exists(osm_bg_image):
		#print "wms", ymax, xorg, yorg, xmax, osm_bg_image
		wms(90, -180, -90, 180, osm_bg_image)
	
	if force or not os.path.exists(sw_osm_image):
		zoom 		= 1
		scale 		= 1	
		rColors 	= list(reversed(hexColors))
		MakeBrowseImage(ds, browse_filename, subset_filename, osm_bg_image, sw_osm_image, levels, rColors, force, verbose, zoom, scale)
		
	ds = None
	
	file_list = [ sw_osm_image, topojson_filename+".gz", filename ]
	CopyToS3( s3_bucket, s3_folder, file_list, 1, 1 )
	
	if not verbose: # Cleanup
		cmd = "rm -rf %s %s %s %s %s %s %s %s" % ( merge_filename, browse_filename, topojson_filename, subset_filename, super_subset_file, subset_aux_filename, geojsonDir, levelsDir)
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
	
# ======================================================================
#	python geos5.py --date 2015-08-10 -v
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)
	
	parser 		= argparse.ArgumentParser(description='GEOS-5 Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 	help="Date")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	
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
	ymd1 		= "%d%02d%02d" % (tomorrow.year, tomorrow.month, tomorrow.day)
	
	mydir 		= os.path.join(config.GEOS5_DIR, ymd)
	if not os.path.exists(mydir):            
		os.makedirs(mydir)
	
	files = []
	for i in range(0,24):	# 0-23
		filename =  "GEOS.fp.fcst.tavg1_2d_flx_Nx.%s_00+%s_%02d30.V01.nc4" %(ymd, ymd, i)
		#filename =  "GEOS.fp.fcst.tavg1_2d_lnd_Nx.%s_00+%s_%02d30.V01.nc4" %(ymd, ymd, i)
		files.append(filename)

	#for i in range(0,24,3):	# 0-23
	#	filename =  "GEOS.fp.fcst.inst3_2d_met_Nx.%s_00+%s_%02d00.V01.nc4" %(ymd, ymd, i)
	#	files.append(filename)

	
	color_file				= os.path.join(basedir, "cluts", "geos5_colors.txt")
	tif_filename			= os.path.join(mydir, "geos5_precip.%s.unflipped.tif" % ymd)
	flipped_tif_filename	= os.path.join(mydir, "geos5_precip.%s.tif" % ymd)
	
	if force or not os.path.exists(tif_filename):          
		if verbose:
			print "file not found",   tif_filename
		get_files(str(year), mydir, files)
	
	for f in files:
		ffilename 		= os.path.join(mydir,f)
		ftif_filename 	= ffilename + ".tif"
		#if force or not os.path.exists(ftif_filename):          
		cmd = "export GDAL_NETCDF_BOTTOMUP=NO; gdal_translate -q -b 1 netcdf:%s:PRECTOT %s" % (ffilename, ftif_filename)
		execute(cmd)
				
	# Now we need to create the 24hr accumulation
	if force or not os.path.exists(tif_filename):          
		for idx, f in enumerate(files):
			ffilename 		= os.path.join(mydir,f)
			ftif_filename 	= ffilename + ".tif"
			ds 				= gdal.Open( ftif_filename )
			band			= ds.GetRasterBand(1)
			data			= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
			
			# data in mm/hour and file is for one hour
			# data is in kg/m2/s... we want results in mm
			# 1hr = 3600s
			
			data			*= 3600
		
			if idx==0:
				total = data
			else:
				total += data
		
		driver 	= gdal.GetDriverByName("GTiff")
		out_ds	= driver.CreateCopy( tif_filename, ds, 0)
		band	= out_ds.GetRasterBand(1)
		band.WriteArray(total, 0, 0)
			
		out_ds	= None
		ds		= None
		
		# Flip it since it is bottom up
		cmd = "flip_raster.py -o %s %s" % ( flipped_tif_filename, tif_filename )
		execute(cmd)
		
	rgb_tif_filename	= os.path.join(mydir, "geos5_precip.%s.flipped.rgb.tif" % ymd)
	if force or (verbose and not os.path.exists(rgb_tif_filename)):	
		cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( flipped_tif_filename, color_file, rgb_tif_filename)
		execute(cmd)
	
	s3_folder	= os.path.join("geos5", str(year), doy)
	region		= config.regions['global']
	s3_bucket	= region['bucket']
	
	process_file( mydir, flipped_tif_filename, s3_bucket, s3_folder)
		
	if not verbose:
		for f in files:
			ffilename 		= os.path.join(mydir,f)
			ftif_filename 	= ffilename + ".tif"
			cmd = "rm %s %s" %(ffilename, ftif_filename)
			execute(cmd)
			cmd = "rm %s %s" %(tif_filename, rgb_tif_filename)

	cleanupdir(config.GEOS5_DIR)