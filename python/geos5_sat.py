#!/usr/bin/env python
#
# Frost Map using GEOS-5 Minimum Surface Air Temperature Product
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
processes	= multiprocessing.cpu_count()

locations = [
	{
		"name":			"Finca Rosa Blanca",
		"latitude":		10.042227,
		"longitude":	-84.1542
	},
	{
		"name":			"Finca Rosa Blanca",
		"latitude":		10.042227,
		"longitude":	-84.1542
	},
	
	
]
def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)

def multiprocessing_download(filepath, local_filename):
	print "multiprocessing_download ", filepath, filename

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
		
def process_file( mydir, filename, s3_bucket, s3_folder, bbox, regionName):
	global force, verbose
	
	print "Processing", filename
	
	geojsonDir	= os.path.join(mydir,"geojson")
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	levelsDir	= os.path.join(mydir,"levels")
	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)

	super_subset_file	= os.path.join(mydir, 			"geos5_sat_super.%s.tif" % ymd)
	merge_filename 		= os.path.join(geojsonDir, 		"geos5_sat.%s.geojson" % ymd)
	topojson_filename 	= os.path.join(geojsonDir, "..", "geos5_sat.%s.topojson" % ymd)
	browse_filename 	= os.path.join(geojsonDir, "..", "geos5_sat.%s_browse.tif" % ymd)
	subset_filename 	= os.path.join(geojsonDir, "..", "geos5_sat.%s_small_browse.tif" % ymd)
	subset_aux_filename	= os.path.join(geojsonDir, "..", "geos5_sat.%s_small_browse.tif.aux.xml" % ymd)
	osm_bg_image		= os.path.join(mydir, "..", 	"osm_bg_%s.png" % regionName )
	sw_osm_image		= os.path.join(geojsonDir, "..", "geos5_sat.%s_thn.jpg" % ymd)
	json_filename		= os.path.join(geojsonDir, 		"geos5_sat.%s.json" % (ymd))
		
	ds 					= gdal.Open( filename )
	geotransform		= ds.GetGeoTransform()
	px					= geotransform[1] / 10
	py					= geotransform[5] / 10
	
	xorg				= geotransform[0]
	yorg  				= geotransform[3]

	xmax				= xorg + geotransform[1]* ds.RasterXSize
	ymax				= yorg + geotransform[5]* ds.RasterYSize
	
	#print ymax, xorg, yorg, xmax
	
	ds					= None

	# upsample and convolve
	if force or not os.path.exists(super_subset_file):
		# we need to have square pixels
		cmd = "gdalwarp -overwrite -q -r cubic -tr %s %s  -co COMPRESS=DEFLATE %s %s" % (str(px), str(py), filename, super_subset_file)
		execute(cmd)
	
	levels 				= [5, 4, 3, 2]
	hexColors 			= [ "ff9a00", "ff0000", "ff99cc", "cc00cc" ]
	
	ds 					= gdal.Open( super_subset_file )
	band				= ds.GetRasterBand(1)
	data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
	
	if force or not os.path.exists(topojson_filename+".gz"):
		for l in levels:
			fileName 		= os.path.join(levelsDir, ymd+"_level_%d.tif"%l)
			CreateLevel(l, geojsonDir, fileName, ds, data, "geos5_sat", force, verbose)
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "geos5_sat_level_%d.geojson"%l)
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
			
		cmd 	= "topojson -p --bbox --simplify-proportion 0.1 -o "+ topojson_filename + " " + merge_filename + quiet
		execute(cmd)

		cmd 	= "gzip -f "+ topojson_filename
			
		execute(cmd)
		
	if not os.path.exists(osm_bg_image):
		ullat = bbox[3]
		ullon = bbox[0]
		lrlat = bbox[1]
		lrlon = bbox[2]
		
		wms(ullat, ullon, lrlat, lrlon, osm_bg_image)
	
	if force or not os.path.exists(sw_osm_image):
		zoom 		= 1
		scale 		= 1
		rColors 	= list(reversed(hexColors))
		MakeBrowseImage(ds, browse_filename, subset_filename, osm_bg_image, sw_osm_image, levels, rColors, force, verbose, zoom, scale)
		
	ds = None
	
	file_list = [ sw_osm_image, topojson_filename+".gz", filename ]
	CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
	
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
#	python geos5_sat.py --date 2016-04-01 --region d02 -v
#

if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)
	
	parser 		= argparse.ArgumentParser(description='GEOS-5 SAT Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 	help="Date")
	apg_input.add_argument("-r", "--region", help="Region", required=1)
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	regionName	= options.region
	
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
	
	region		= config.regions[regionName]
	assert(region)
	
	mydir 		= os.path.join(config.GEOS5_SAT_DIR, ymd)
	if not os.path.exists(mydir):            
		os.makedirs(mydir)
	
	files = []
	for i in range(0,24):	# 0-23
		filename =  "GEOS.fp.fcst.tavg1_2d_flx_Nx.%s_00+%s_%02d30.V01.nc4" %(ymd, ymd, i)
		#filename =  "GEOS.fp.fcst.tavg1_2d_lnd_Nx.%s_00+%s_%02d30.V01.nc4" %(ymd, ymd, i)
		files.append(filename)
	
	color_file				= os.path.join(basedir, "cluts", "geos5_colors.txt")
	tif_filename			= os.path.join(mydir, "geos5_sat.%s.unflipped.tif" % ymd)
	flipped_tif_filename	= os.path.join(mydir, "geos5_sat.%s.tif" % ymd)
	
	regionDir				= os.path.join(mydir, regionName)
	if not os.path.exists(regionDir):            
		os.makedirs(regionDir)
	subset_tif_filename		= os.path.join(regionDir, "geos5_sat.%s.%s.tif" % (regionName, ymd))
	
	if force or not os.path.exists(tif_filename):          
		if verbose:
			print "file not found",   tif_filename
		get_files(str(year), mydir, files)
	
	for f in files:
		ffilename 		= os.path.join(mydir,f)
		ftif_filename 	= ffilename + ".tif"
		#if force or not os.path.exists(ftif_filename):          
		cmd = "export GDAL_NETCDF_BOTTOMUP=NO; gdal_translate -q -b 1 netcdf:%s:TLML %s" % (ffilename, ftif_filename)
		execute(cmd)
				
	if force or not os.path.exists(tif_filename):  
		if verbose:
			print "Creating ", tif_filename
			
		for idx, f in enumerate(files):
			ffilename 		= os.path.join(mydir,f)
			ftif_filename 	= ffilename + ".tif"
			ds 				= gdal.Open( ftif_filename )
			band			= ds.GetRasterBand(1)
			data			= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
			projection  	= ds.GetProjection()
			geotransform	= ds.GetGeoTransform()
					
			if idx==0:
				minTemp = numpy.array(data)
			else:
				minTemp = numpy.minimum(minTemp, data)
		
		minTemp[minTemp>288]	= 1 # no frost
		minTemp[minTemp>270]	= 2 # minor frost
		minTemp[minTemp>260]	= 3 # moderate frost
		minTemp[minTemp>250]	= 4 # severe frost
		minTemp[minTemp>5]		= 5 # very severe frost
		
		driver 	= gdal.GetDriverByName("GTiff")
		out_ds	= driver.Create( tif_filename, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Byte, [ 'COMPRESS=DEFLATE' ] )
		band	= out_ds.GetRasterBand(1)
		band.WriteArray(minTemp, 0, 0)
		
		ct = gdal.ColorTable()
		ct.SetColorEntry( 0, (255, 255, 255, 255) )
		ct.SetColorEntry( 1, (0, 255, 0, 255) )
		ct.SetColorEntry( 2, (255, 154, 0, 255) )
		ct.SetColorEntry( 3, (255, 0, 0, 255) )
		ct.SetColorEntry( 4, (255, 153, 204, 255) )
		ct.SetColorEntry( 5, (204, 0, 204, 255) )
		band.SetRasterColorTable(ct)
		
		out_ds.SetGeoTransform( geotransform )
		out_ds.SetProjection( projection )
		
		out_ds	= None
		ds		= None
		
		print "Saved", tif_filename
		
		# Flip it since it is bottom up
		cmd = "flip_raster.py -pct -o %s %s" % ( flipped_tif_filename, tif_filename )
		execute(cmd)
	else:
		print "File exists", tif_filename
			
	s3_folder	= os.path.join("geos5_sat", str(year), doy)
	s3_bucket	= region['bucket']
	
	bbox		= region['bbox']
	if force or not os.path.exists(subset_tif_filename):
		cmd = "gdalwarp -overwrite -q -te %f %f %f %f %s %s" % (bbox[0], bbox[1], bbox[2], bbox[3], flipped_tif_filename, subset_tif_filename)
		execute(cmd)
	
	process_file( regionDir, subset_tif_filename, s3_bucket, s3_folder, bbox, regionName)
		
	if not verbose:
		for f in files:
			ffilename 		= os.path.join(mydir,f)
			ftif_filename 	= ffilename + ".tif"
			cmd = "rm %s %s" %(ffilename, ftif_filename)
			execute(cmd)
			cmd = "rm %s %s" %(tif_filename, flipped_tif_filename)
			execute(cmd)

	cleanupdir(config.GEOS5_SAT_DIR)