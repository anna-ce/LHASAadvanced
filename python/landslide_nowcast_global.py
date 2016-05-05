#!/usr/bin/env python
#
# Created on 03/02/2016 Pat Cappelaere - Vightel Corporation
#
# Generates 24hr Forecast Landslide Estimate
#

import numpy, sys, os, glob, inspect, urllib, shutil
import argparse

from osgeo import osr, gdal
from ftplib import FTP
import datetime
from datetime import date, timedelta
from which import *
from dateutil.parser import parse

import json

from browseimage import MakeBrowseImage, wms
from s3 import CopyToS3

# Site configuration
import config

force 		= 0
verbose 	= 0
ymd 		= config.ymd
ftp_site 	= "jsimpson.pps.eosdis.nasa.gov"

early_gis_path 	= "/data/imerg/gis/early"
late_gis_path	= "/data/imerg/gis/"

def execute(cmd):
	if(verbose):
		print cmd
	os.system(cmd)

def CreateLevel(l, geojsonDir, fileName, src_ds, data, attr, _force, _verbose):
	global force, verbose
	force 				= _force
	verbose				= _verbose
	
	if verbose:
		print "CreateLevel", l, _force, _verbose
	
	projection  		= src_ds.GetProjection()
	geotransform		= src_ds.GetGeoTransform()
	#band				= src_ds.GetRasterBand(1)
		
	xorg				= geotransform[0]
	yorg  				= geotransform[3]
	xres				= geotransform[1]
	yres				= -geotransform[5]
	stretch				= 1	# xres/yres
	
	if verbose:
		print xres, yres, stretch
		
	xmax				= xorg + geotransform[1]* src_ds.RasterXSize
	ymax				= yorg + geotransform[5]* src_ds.RasterYSize


	if not force and os.path.exists(fileName):
		return
		
	driver 				= gdal.GetDriverByName( "GTiff" )

	dst_ds_dataset		= driver.Create( fileName, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte, [ 'COMPRESS=DEFLATE' ] )
	dst_ds_dataset.SetGeoTransform( geotransform )
	dst_ds_dataset.SetProjection( projection )
	o_band		 		= dst_ds_dataset.GetRasterBand(1)
	o_data				= o_band.ReadAsArray(0, 0, dst_ds_dataset.RasterXSize, dst_ds_dataset.RasterYSize )
	
	count 				= (data >= l).sum()	

	o_data[data>=l] 	= 255
	o_data[data<l]		= 0

	if verbose:
		print "*** Level", l, " count:", count

	if count > 0 :

		dst_ds_dataset.SetGeoTransform( geotransform )
			
		dst_ds_dataset.SetProjection( projection )
		
		o_band.WriteArray(o_data, 0, 0)
		
		ct = gdal.ColorTable()
		ct.SetColorEntry( 0, (255, 255, 255, 255) )
		ct.SetColorEntry( 255, (255, 0, 0, 255) )
		o_band.SetRasterColorTable(ct)
		
		dst_ds_dataset 	= None
		if verbose:
			print "Created", fileName

		cmd = "gdal_translate -q -of PNM " + fileName + " "+fileName+".pgm"
		execute(cmd)

		# -i  		invert before processing
		# -t 2  	suppress speckles of up to this many pixels. 
		# -a 1.5  	set the corner threshold parameter
		# -z black  specify how to resolve ambiguities in path decomposition. Must be one of black, white, right, left, minority, majority, or random. Default is minority
		# -x 		scaling factor
		# -L		left margin
		# -B		bottom margin

		if stretch != 1:
			cmd = str.format("potrace -i -z black -a 1.5 -t 3 -b geojson -o {0} {1} -x {2} -S {3} -L {4} -B {5} ", fileName+".geojson", fileName+".pgm", xres, stretch, xorg, ymax ); 
		else:
			cmd = str.format("potrace -i -z black -a 3 -t 4 -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", fileName+".geojson", fileName+".pgm", xres, xorg, ymax ); 
			
		execute(cmd)
	
		#cmd = str.format("topojson -o {0} --simplify-proportion 0.5 -p {3}={1} -- {3}={2} > /dev/null 2>&1", fileName+".topojson", l, fileName+".geojson", attr );
		out = ""
		if not verbose:
			out = "> /dev/null 2>&1"
			
		cmd = str.format("topojson -q 1e6 -s 0.0000001 -o {0} -p {3}={1} -- {3}={2} {4}", fileName+".topojson", l, fileName+".geojson", attr, out ); 
		execute(cmd)
	
		# convert it back to json
		cmd = "topojson-geojson --precision 4 -o %s %s" % ( geojsonDir, fileName+".topojson" )
		execute(cmd)
	
		# rename file
		output_file = "%s_level_%d.geojson" % (attr, l)
		json_file	= "%s.json" % attr
		cmd = "mv %s %s" % (os.path.join(geojsonDir,json_file), os.path.join(geojsonDir, output_file))
		execute(cmd)
		
def save_tif(fname, data, ds, type, ct):
	if force or not os.path.exists(fname):
		if verbose:
			print "saving", fname
		
		format 		= "GTiff"
		driver 		= gdal.GetDriverByName( format )
		#dst_ds	 	= driver.Create( fname, ds.RasterXSize, ds.RasterYSize, 1, type, [ 'COMPRESS=DEFLATE' ] )
		dst_ds	 	= driver.Create( fname, ds.RasterXSize, ds.RasterYSize, 1, type, ['COMPRESS=DEFLATE'] )
		band 		= dst_ds.GetRasterBand(1)
		
		dst_ds.SetGeoTransform( ds.GetGeoTransform() )
		dst_ds.SetProjection( ds.GetProjection() )
	
		if ct:
			ct = gdal.ColorTable()
			ct.SetColorEntry( 0, (0, 0, 0, 0) )
			ct.SetColorEntry( 1, (255, 255, 0, 255) )
			ct.SetColorEntry( 2, (255, 0, 0, 255) )
			ct.SetColorEntry( 3, (255, 0, 255, 0) )
			band.SetRasterColorTable(ct)
	
		band.WriteArray( data )

		dst_ds = None
	else:
		pass
	
def get_late_gpm_files(gis_files, product_name, ymd_org):
	global force, verbose
	downloaded_files = []
	
	err = 0
		
	try:
		ftp = FTP(ftp_site)
	
		ftp.login('pat@cappelaere.com','pat@cappelaere.com')               					# user anonymous, passwd anonymous@
	
	except Exception as e:
		print "FTP login Error", sys.exc_info()[0], e
		print "Exception", e
		sys.exit(-1)

	for f in gis_files:
		# Check the year and month, we may be ahead
		arr 	= f.split(".")
		ymdarr	= arr[4].split("-")
		ymd		= ymdarr[0]
		month	= ymd[4:6]
		
		mydir	= os.path.join(config.data_dir, product_name, ymd_org)		
		if not os.path.exists(mydir):
		    os.makedirs(mydir)
			
		filepath = late_gis_path+ "%s" % ( month)
		
		ftp.cwd(filepath)
		local_filename = os.path.join(mydir, f)
		if not os.path.exists(local_filename):
			file = open(local_filename, 'wb')
			try:
				ftp.retrbinary("RETR " + f, file.write)
				if verbose:
					print "Downloading...", f, " to ", local_filename
				file.close()
				downloaded_files.append(f)
			except Exception as e:
				if verbose:
					print "GPM IMERG FTP Error", filepath, e					
				os.remove(local_filename)
				err = 1

	ftp.close()
	
	if err:
		sys.exit(-1)
		
	return gis_files

def process(_dir, files, ymd):
	weights = [ 1.00000000, 0.25000000, 0.11111111, 0.06250000, 0.04000000, 0.02777778, 0.02040816]
	sum		= 1.511797
	
	i 		= 0

	global total
	 
	for f in files:
		if f.find(".1day.tif")>0:
			fname	= os.path.join(_dir, f)
			ds 		= gdal.Open( fname )
			band	= ds.GetRasterBand(1)
			data	= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )
			if verbose:
				print "Process", i, weights[i], f, ds.RasterXSize, ds.RasterYSize
				
			# data in 10 * mm
			if i == 0:
				total = data
				total /= 10.0
			else:
				total += data * weights[i] / 10.0
					
			i 		+= 1
			ds 		= None
			
	total /= sum
	
	# Get ARI files
	ARI90 	= os.path.join(config.data_dir, "ant_r", "ARI90.tif")
	ARI95 	= os.path.join(config.data_dir, "ant_r", "ARI95.tif")
	
	ds_90 	= gdal.Open( ARI90 )
	band_90	= ds_90.GetRasterBand(1)
	ndata	= band_90.GetNoDataValue()
		
	data_90	= band_90.ReadAsArray(0, 0, ds_90.RasterXSize, ds_90.RasterYSize ).astype(numpy.float)
	
	ds_95 	= gdal.Open( ARI95 )
	band_95	= ds_95.GetRasterBand(1)
	data_95	= band_95.ReadAsArray(0, 0, ds_95.RasterXSize, ds_95.RasterYSize ).astype(numpy.float)
	
	total[total<=data_90] 	= 0
	total[total>data_95] 	= 2
	total[total>data_90] 	= 1
	total[data_90 < 0]		= 0

	fname 		= os.path.join(_dir, "total.tif")
	
	if force or not os.path.exists(fname):
		save_tif(fname, total, ds_95, gdal.GDT_Byte, 1)
	
	dst_ds 		= None
	ds_90		= None
	ds_95		= None
	
	# Get susmap
	susmap 		= os.path.join(config.data_dir, "susmap.2", "global.tif")
	ds2			= gdal.Open( susmap )
	band_2		= ds2.GetRasterBand(1)
	data_2		= band_2.ReadAsArray(0, 0, ds2.RasterXSize, ds2.RasterYSize )
		
	# Supersample it to 1km
	fname_1km 	= os.path.join(_dir, "total_1km.tif")
	if force or not os.path.exists(fname_1km):
		if verbose:
			print "supersampling to 1km..."

		#cmd 		= "gdal_translate -outsize 43167 21600 -co 'COMPRESS=DEFLATE' %s %s" % (fname, fname_1km)
		cmd 		= "gdalwarp -q -overwrite -co 'COMPRESS=DEFLATE' -ts %d %d %s %s" % (ds2.RasterXSize, ds2.RasterYSize, fname, fname_1km)

		if force or not os.path.exists(fname_1km):
			execute(cmd)
	
	# Get susceptibility map
	if verbose:
		print "checking against susceptibility map..."

	ds1					= gdal.Open( fname_1km )
	band_1				= ds1.GetRasterBand(1)
	data_1				= band_1.ReadAsArray(0, 0, ds1.RasterXSize, ds1.RasterYSize )

	data_1[data_2<2] 	= 0
	
	fname_1km_final 	= os.path.join(_dir, "global_landslide_nowcast_%s.tif"%ymd)
	
	if force or not os.path.exists(fname_1km_final):
		save_tif(fname_1km_final, data_1, ds2, gdal.GDT_Byte, 1)
	
	levels 				= [2,1]
	hexColors 			= ["#feb24c","#f03b20"]
	
	geojsonDir			= os.path.join(_dir,"geojson")
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	levelsDir			= os.path.join(_dir,"levels")
	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)
		
	topojson_filename 	= os.path.join(_dir, "global_landslide_nowcast_%s.topojson" % ymd)
	merge_filename 		= os.path.join(geojsonDir, "global_landslide_nowcast_%s.geojson" % ymd)
	attr				= "nowcast"
	if force or not os.path.exists(topojson_filename+".gz"):
		for l in levels:
			fileName 		= os.path.join(levelsDir, "global_level_%d.tif"%l)
			CreateLevel(l, geojsonDir, fileName, ds1, data_1, attr, force,verbose)
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "%s_level_%d.geojson"%(attr,l))
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
		cmd 	= "topojson -p -o "+ topojson_filename + " " + merge_filename + " > /dev/null 2>&1"
		execute(cmd)

		cmd 	= "gzip -f --keep "+ topojson_filename
		execute(cmd)
		
	osm_bg_image		= os.path.join(_dir, "..", "osm_bg.png")
	sw_osm_image		= os.path.join(_dir, "global_landslide_nowcast_%s_thn.jpg" % ymd)
	
	browse_filename		= os.path.join(geojsonDir, "global_browse_%s.tif" % ymd)
	subset_filename 	= os.path.join(geojsonDir, "global.%s_small_browse.tif" % (ymd))
	transparent			= os.path.join(geojsonDir, "global.%s_small_browse_transparent.tif" % (ymd))
	
	if not os.path.exists(osm_bg_image):
		ullat = 85
		ullon = -180
		lrlat = -85
		lrlon = 180
		
		print "wms", ullat, ullon, lrlat, lrlon
		wms(ullat, ullon, lrlat, lrlon, osm_bg_image)
	
	
	#if force or not os.path.exists(sw_osm_image):
	#	MakeBrowseImage(ds1, browse_filename, subset_filename, osm_bg_image, sw_osm_image,levels, hexColors, force, verbose, zoom)

	# Make a small browse image
	if force or not os.path.exists(browse_filename):
		cmd = "gdalwarp -q -te -180 -85 180 85 -tr 0.5 0.5 %s %s" %(fname_1km_final, browse_filename)
		execute(cmd)
	
	if force or not os.path.exists(transparent):
		cmd = "convert %s -transparent black %s" %(browse_filename, transparent)
		execute(cmd)
	
	if force or not os.path.exists(sw_osm_image):
		cmd = "composite -quiet -gravity center -blend 60 %s %s %s" %( transparent, osm_bg_image, sw_osm_image)
		execute(cmd)
	
	ds1 = None
	ds2 = None
	
	file_list = [ sw_osm_image, topojson_filename+".gz", fname_1km_final ]
	CopyToS3( s3_bucket, s3_folder, file_list, 1, 1 )
	
	if not verbose: # Cleanup
		gpm_files = os.path.join(_dir, "3B-HHR*")
		cmd = "rm -rf %s %s %s %s %s %s" % (gpm_files, fname_1km, fname, topojson_filename, geojsonDir, levelsDir)
		execute(cmd)
		
def get_gpm_files( _dir, files):
	print files
	
def cleanupdir( mydir, product_name):
	if verbose:
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
	_dir			=  os.path.join(config.data_dir, product_name)
	cleanupdir(_dir, product_name)
	
	
# =======================================================================
# Main
# python landslide_nowcast_global.py --date 2016-02-29 -v
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='Generate Forecast Landslide Estimates')
	apg_input 	= parser.add_argument_group('Input')
		
	apg_input.add_argument("-f", "--force", 	action='store_true', help="Forces new products to be generated")
	apg_input.add_argument("-v", "--verbose", 	action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 		help="date: 2014-11-20 or today if not defined")
	
	todaystr		= date.today().strftime("%Y-%m-%d")
	
	options 		= parser.parse_args()
	force			= options.force
	verbose			= options.verbose
	dt				= options.date or todaystr
	
	basedir 		= os.path.dirname(os.path.realpath(sys.argv[0]))
	
	today			= parse(dt)
	year			= today.year
	month			= today.month
	day				= today.day
	ymd				= "%d%02d%02d" % (year, month, day)
	doy				= today.strftime('%j')
	product_name	= "global_landslide_nowcast"
	s3_folder		= os.path.join(product_name, str(year), doy)
	
	region			= config.regions['global']
	s3_bucket		= region['bucket']

	_dir	= os.path.join(config.data_dir, product_name, ymd)
	if not os.path.exists(_dir):
	    os.makedirs(_dir)
	
	if verbose:
		print "generating landslide global nowcast for", today.strftime("%Y-%m-%d")
		
	# Get last 7 days
	files = []
	for i in range(0,7):
		dt	 				= today + datetime.timedelta(days= -i-1)
		year				= dt.year
		month				= dt.month
		day					= dt.day

		gis_file_day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.1day.tif"%(year, month, day)
		gis_file_day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.1day.tfw"%(year, month, day)

		files.append(gis_file_day)
		files.append(gis_file_day_tfw)
		
	get_late_gpm_files(files, product_name, ymd)
	process(_dir, files, ymd)
	
	cleanup()
	
	if verbose:
		print "Done."
