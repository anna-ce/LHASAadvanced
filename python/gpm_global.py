#!/usr/bin/env python
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

import config

from browseimage import MakeBrowseImage, wms
from s3 import CopyToS3
#from level import CreateLevel


verbose 	= 0
force 		= 0
ftp_site 	= "jsimpson.pps.eosdis.nasa.gov"
#gis_path 	= "pub/merged/3B42RT/"

early_gis_path 	= "/data/imerg/gis/early"
late_gis_path	= "/data/imerg/gis/"


def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)

#def CreateLevel(maxl, minl, geojsonDir, fileName, src_ds, data, attr):
def CreateLevel(l, geojsonDir, fileName, src_ds, data, attr):
	global force, verbose
		
	minl				= l
	projection  		= src_ds.GetProjection()
	geotransform		= src_ds.GetGeoTransform()
	#band				= src_ds.GetRasterBand(1)
		
	xorg				= geotransform[0]
	yorg  				= geotransform[3]
	pres				= geotransform[1]
	xmax				= xorg + geotransform[1]* src_ds.RasterXSize
	ymax				= yorg - geotransform[1]* src_ds.RasterYSize


	if not force and os.path.exists(fileName):
		return
		
	driver 				= gdal.GetDriverByName( "GTiff" )

	dst_ds_dataset		= driver.Create( fileName, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte, [ 'COMPRESS=DEFLATE' ] )
	dst_ds_dataset.SetGeoTransform( geotransform )
	dst_ds_dataset.SetProjection( projection )
	o_band		 		= dst_ds_dataset.GetRasterBand(1)
	o_data				= o_band.ReadAsArray(0, 0, dst_ds_dataset.RasterXSize, dst_ds_dataset.RasterYSize )
	
	#o_data.fill(255)
	#o_data[data>=maxl] 	= 0
	#o_data[data<minl]	= 0
	
	o_data[data>=l]		= 255
	o_data[data<l]		= 0

	count 				= (o_data > 0).sum()	
	if verbose:
		print "Level", minl, " count:", count

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

		cmd = str.format("potrace -i -z black -a 1.5 -t 3 -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", fileName+".geojson", fileName+".pgm", pres, xorg, ymax ); 
		execute(cmd)

		#cmd = str.format("node set_geojson_property.js --file {0} --prop frost={1}", fileName+".geojson", frost)
		#execute(cmd)
	
		#cmd = str.format("topojson -o {0} --simplify-proportion 0.5 -p {3}={1} -- {3}={2}", fileName+".topojson", l, fileName+".geojson", attr ); 
		quiet = " > /dev/null 2>&1"
		if verbose:
			quiet = " "
			
		cmd = str.format("topojson --bbox --simplify-proportion 0.5 -o {0} --no-stitch-poles -p {3}={1} -- {3}={2} {4}", fileName+".topojson", minl, fileName+".geojson", attr, quiet ); 
		execute(cmd)
	
		# convert it back to json
		cmd = "topojson-geojson --precision 4 -o %s %s" % ( geojsonDir, fileName+".topojson" )
		execute(cmd)
	
		# rename file
		output_file = "%s_level_%d.geojson" % (attr, minl)
		json_file	= "%s.json" % attr
		cmd 		= "mv %s %s" % (os.path.join(geojsonDir,json_file), os.path.join(geojsonDir, output_file))
		execute(cmd)
		

def get_late_gpm_files(gis_files, product_name):
	global force, verbose
	downloaded_files = []
		
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
		mydir	= os.path.join(config.data_dir, product_name, ymd)
		
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

	ftp.close()
	return gis_files
	
def get_early_gpm_files(trmm_gis_files):
	global force, verbose
	downloaded_files = []
		
	try:
		ftp = FTP(ftp_site)
	
		ftp.login('pat@cappelaere.com','pat@cappelaere.com')               					# user anonymous, passwd anonymous@
	
	except Exception as e:
		print "FTP login Error", sys.exc_info()[0], e
		print "Exception", e
		sys.exit(-1)

	for f in trmm_gis_files:
		# Check the year and month, we may be ahead
		arr 	= f.split(".")
		ymdarr	= arr[4].split("-")
		ymd		= ymdarr[0]
		month	= ymd[4:6]
		mydir	= os.path.join(config.data_dir, "gpm", ymd)
		
		if not os.path.exists(mydir):
		    os.makedirs(mydir)
			
		#filepath = gis_path+ "%s" % ( month)
		filepath = early_gis_path
		
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

	ftp.close()
	return trmm_gis_files
	
def save_tif(fname, data, ds, type, colors):
	if verbose:
		print "saving", fname
		
	format 		= "GTiff"
	driver 		= gdal.GetDriverByName( format )
	dst_ds	 	= driver.Create( fname, ds.RasterXSize, ds.RasterYSize, 1, type, [ 'COMPRESS=DEFLATE' ] )
	band 		= dst_ds.GetRasterBand(1)
	
	band.WriteArray( data )
	
	dst_ds.SetGeoTransform( ds.GetGeoTransform() )
	dst_ds.SetProjection( ds.GetProjection() )
	
	ct = gdal.ColorTable()
	ct.SetColorEntry( 0, (0, 0, 0, 0) )
	ct.SetColorEntry( 1, (255, 0, 0, 255) )
	band.SetRasterColorTable(ct)
	
	dst_ds = None
		
#
# Return appropriate color table for product (and levels)
#
def color_table(name):
	color_file = None
	
	if name=='gpm_1d':
		color_file	= os.path.join(basedir, "cluts", "gpm_1d.txt")
	if name=='gpm_3d':
		color_file	= os.path.join(basedir, "cluts", "gpm_3d.txt")
	if name=='gpm_7d':
		color_file	= os.path.join(basedir, "cluts", "gpm_7d.txt")
	if name=='gpm_30mn':
		color_file	= os.path.join(basedir, "cluts", "gpm_30mn.txt")
	if name=='gpm_3hrs':
		color_file	= os.path.join(basedir, "cluts", "gpm_3hrs.txt")
	
	if (color_file == None) or not os.path.exists(color_file):
		print "Invalid color table for", name
		sys.exit(-1)
			
	return color_file
	
def process(gpm_dir, name, gis_file_day, ymd ):
	global force, verbose, levels, hexColors

	regionName = 'global'
	
	region_dir	= os.path.join(gpm_dir,regionName)
	if not os.path.exists(region_dir):            
		os.makedirs(region_dir)
	
	origFileName 		= os.path.join(gpm_dir,gis_file_day)
	
	if not os.path.exists(origFileName):
		print "File does not exist", origFileName
		return
	
	ds 						= gdal.Open(origFileName)
	geotransform			= ds.GetGeoTransform()

	xorg					= geotransform[0]
	yorg  					= geotransform[3]
	pixelsize				= geotransform[1]
	xmax					= xorg + geotransform[1]* ds.RasterXSize
	ymax					= yorg - geotransform[1]* ds.RasterYSize
	
	bbox					= [xorg, ymax, xmax, yorg]
	
	geojsonDir				= os.path.join(region_dir,"geojson_%s" % (name))
	levelsDir				= os.path.join(region_dir,"levels_%s" % (name))

	origFileName_tfw		= origFileName.replace(".tif", ".tfw")
	supersampled_file		= os.path.join(region_dir, "%s.%s_x2.tif" % (name, ymd))
	merge_filename 			= os.path.join(geojsonDir, "%s.%s.geojson" % (name, ymd))
	topojson_filename 		= os.path.join(geojsonDir, "..", "%s.%s.topojson" % (name,ymd))
	topojson_gz_filename 	= os.path.join(region_dir, "%s.%s.topojson.gz" % (name,ymd))
	browse_filename 		= os.path.join(geojsonDir, "..", "%s.%s_browse.tif" % (name,ymd))
	subset_aux_filename 	= os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif.aux.xml" % (name, ymd))
	subset_filename 		= os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif" % (name, ymd))
	osm_bg_image			= os.path.join(config.data_dir, "gpm", "osm_bg.png")	
	sw_osm_image			= os.path.join(geojsonDir, "..", "%s.%s_thn.png" % (name, ymd))
	tif_image				= os.path.join(geojsonDir, "..", "%s.%s.tif" % (name, ymd))
	rgb_tif_image			= os.path.join(geojsonDir, "..", "%s.%s.rgb.tif" % (name, ymd))
	geojson_filename 		= os.path.join(geojsonDir, "..", "%s.%s.json" % (name,ymd))

	if not force and os.path.exists(topojson_gz_filename):
		print "return Found", topojson_gz_filename
		return
	
	print "Processing", gis_file_day, topojson_gz_filename
	
	if force or not os.path.exists(supersampled_file):
		cmd 			= "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -co COMPRESS=LZW %s %s"%(pixelsize/2, pixelsize/2, bbox[0], bbox[1], bbox[2], bbox[3], origFileName, supersampled_file)
		execute(cmd)
	
	if not os.path.exists(geojsonDir):            
		os.makedirs(geojsonDir)

	if not os.path.exists(levelsDir):            
		os.makedirs(levelsDir)

	#levels 				= [377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3]
		
	# http://hclwizard.org/hcl-color-scheme/
	# http://vis4.net/blog/posts/avoid-equidistant-hsv-colors/
	# from http://tristen.ca/hcl-picker/#/hlc/12/1/241824/55FEFF
	# Light to dark
	# hexColors 			= [ "#56F6FC","#58DEEE","#5BC6DE","#5EAFCC","#5E99B8","#5D84A3","#596F8D","#535B77","#4A4861","#3F374B","#322737","#241824"]
	
	# GPM palette
	#hexColors 			= [ "#f7fcf0","#e0f3db","#ccebc5","#a8ddb5","#7bccc4","#4eb3d3","#2b8cbe","#0868ac","#084081","#810F7C","#4D004A" ]
	
	# Current Green-Red GPM Palette & Levels
	# Data in file is multiplied by 10 and are in mm
	#levels				= [ 500, 200, 100, 50, 30, 20, 10, 5, 3, 2, 1]
		
	if verbose:
		switch(name)
		color_file		= color_table(name)
		if force or (verbose and not os.path.exists(rgb_tif_image)):	
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( supersampled_file, color_file, rgb_tif_image)
			execute(cmd)
	
	ds 					= gdal.Open( supersampled_file )
	band				= ds.GetRasterBand(1)
	data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )

	data[data>9000]		= 0					# No value
	sdata 				= data/10			# back to mm
	
	if force or not os.path.exists(topojson_filename+".gz"):
		for idx, l in enumerate(levels):
			#print "level", idx
			#if idx < len(levels)-1:
			fileName 		= os.path.join(levelsDir, ymd+"_level_%d.tif"%l)
			#CreateLevel(l, levels[idx+1], geojsonDir, fileName, ds, sdata, "precip")
			CreateLevel(l, geojsonDir, fileName, ds, sdata, "precip")
	
		jsonDict = dict(type='FeatureCollection', features=[])
	
		for l in reversed(levels):
			fileName 		= os.path.join(geojsonDir, "precip_level_%d.geojson"%l)
			if os.path.exists(fileName):
				with open(fileName) as data_file:    
					jdata = json.load(data_file)
		
				if 'features' in jdata:
					for f in jdata['features']:
						jsonDict['features'].append(f)
	

		with open(merge_filename, 'w') as outfile:
		    json.dump(jsonDict, outfile)	

		quiet = " > /dev/null 2>&1"
		#if verbose:
		#	quiet = " "
				
		# Convert to topojson
		cmd 	= "topojson --no-stitch-poles --bbox -p precip -o "+ topojson_filename + " " + merge_filename + quiet
		execute(cmd)

		cmd 	= "gzip -f --keep "+ topojson_filename
		execute(cmd)
	
	# Convert to shapefile		
	#if 1: #and os.path.exists(merge_filename):
	#	cmd= "ogr2ogr -f 'ESRI Shapefile' %s %s" % ( shpDir, merge_filename)
	#	execute(cmd)
	
	#if force or not os.path.exists(shp_zip_file):
	#	#cmd 	= "cd %s; tar -cvzf %s shp" %(region_dir, shapefile_gz)
	#	cmd 	= "cd %s; zip %s shp_%s/*" %(region_dir, shp_zip_file, name)
	#	execute(cmd)
		
	# problem is that we need to scale it or adjust the levels for coloring (easier)
	def scale(x): return x*10
	adjusted_levels = map(scale, levels)
	#adjusted_levels 		= [3770, 2330, 1440, 890, 550, 340, 210, 130, 80, 50, 30]
	
	if not os.path.exists(osm_bg_image):
		if verbose:
			print "wms", ymax, xorg, yorg, xmax, osm_bg_image
		wms(yorg, xorg, ymax, xmax, osm_bg_image)
			
	zoom = 2
	if force or not os.path.exists(sw_osm_image):
		rColors 	= list(reversed(hexColors))
		MakeBrowseImage(ds, browse_filename, subset_filename, osm_bg_image, sw_osm_image, adjusted_levels, rColors, force, verbose, zoom)
	
	if force or not os.path.exists(tif_image):
		cmd 				= "gdalwarp -overwrite -q -co COMPRESS=LZW %s %s"%( origFileName, tif_image)
		execute(cmd)
		
	ds = None
	
	file_list = [ sw_osm_image, topojson_filename+".gz", tif_image ]
	CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
	
	if not verbose: # Cleanup
		cmd = "rm -rf %s %s %s %s %s %s %s %s %s %s" % (origFileName, origFileName_tfw, supersampled_file, merge_filename, topojson_filename, subset_aux_filename, browse_filename, subset_filename, geojsonDir, levelsDir)
		execute(cmd)

#
# Get 30mn files every 30mn
#
def process_30mn_files(gpm_dir, startTime):
	hour 		= startTime.hour

	# we need to start at the next 3hr increment
	hour 		= int(math.ceil(hour/3)*3)
	
	if hour > 24:
		startTime = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
		hour = 0
		
	startTime	= datetime.datetime(startTime.year, startTime.month, startTime.day, hour, 0, 0)
		
	minute 		= hour*60
	files		= []
	today		= datetime.datetime.utcnow()
	dt			= startTime
	
	while dt< today:
		year	= startTime.year
		month	= startTime.month
		day		= startTime.day
		sh 		= startTime.hour
		sm		= startTime.minute
		ss		= startTime.second
		em		= sm + 29
		
		dt					= datetime.datetime(year, month, day, sh,em,0)

		#gis_file_3hr 		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S%02d%02d00-E%02d%d59.%04d.V03E.3hr.tif"%(year, month, day,sh,sm,sh,em,minute)
		#gis_file_3hr_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S%02d%02d00-E%02d%d59.%04d.V03E.3hr.tfw"%(year, month, day,sh,sm,sh,em,minute)

		gis_file_30mn 		= "3B-HHR-E.MS.MRG.3IMERG.%d%02d%02d-S%02d%02d00-E%02d%d59.%04d.V03E.30min.tif"%(year, month, day,sh,sm,sh,em,minute)
		gis_file_30mn_tfw 	= "3B-HHR-E.MS.MRG.3IMERG.%d%02d%02d-S%02d%02d00-E%02d%d59.%04d.V03E.30min.tfw"%(year, month, day,sh,sm,sh,em,minute)
		
		if verbose:
			print gis_file_30mn

		files.append(gis_file_30mn)
		files.append(gis_file_30mn_tfw)
		
		minute += 30
		startTime += datetime.timedelta(minutes=30)

		if	minute >= 1440:
			minute = 0
	
	if verbose:
		print "Get 30mn files...."

	downloaded_files = get_early_gpm_files(files)
	
	# Process them
	for f in downloaded_files:
		try:
			if f.index(".30min.tif"):
				arr 	= f.split("-")
				arr2	= arr[2].split(".")
				arr3	= arr[4].split(".")
				
				ymd		= arr2[4]
				gpm_dir	= os.path.join(config.data_dir, "gpm", ymd)
						
				process(gpm_dir, "gpm_30mn", f, ymd+"."+arr3[0][1:])
		except ValueError:
			pass
	
#
# Get 3hr files every 3 hrs and the 1-day files so we can run the landslide model every 3hrs
# Files are available within 8-12 hrs
#
def process_3hrs_files(gpm_dir, startTime):
	
	hour 		= startTime.hour
	files		= []
	today		= datetime.datetime.utcnow()
	
	
	# we need to start at the next 3hr increment
	hour 		= int(math.ceil(hour/3)*3) -1
	if hour < 0:
		hour = 0
		
	minute		= ((hour+1) * 60) - 30
		
	if hour > 23:
		startTime = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
		hour = 0
		
	startTime	= datetime.datetime(startTime.year, startTime.month, startTime.day, hour, 0, 0)
	dt			= startTime
	
	print "starting at:", startTime
	
	while dt <= today:
		year	= startTime.year
		month	= startTime.month
		day		= startTime.day
		sh 		= startTime.hour
		sm		= startTime.minute
		ss		= startTime.second
		
		minute	= sh*60 + 30
			
		dt						= datetime.datetime(year, month, day, sh, 0, 0)
		if( dt < today):	
			gis_file_3hr 		= "3B-HHR-E.MS.MRG.3IMERG.%d%02d%02d-S%02d3000-E%02d5959.%04d.V03E.3hr.tif"%(year, month, day,sh,sh,minute)
			gis_file_3hr_tfw 	= "3B-HHR-E.MS.MRG.3IMERG.%d%02d%02d-S%02d3000-E%02d5959.%04d.V03E.3hr.tfw"%(year, month, day,sh,sh,minute)

			# REMOVED
			#gis_file_1day 		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S%02d3000-E%02d5959.%04d.V03E.1day.tif"%(year, month, day,sh,sh,minute)
			#gis_file_1day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S%02d3000-E%02d5959.%04d.V03E.1day.tfw"%(year, month, day,sh,sh,minute)
		
			if verbose:
				print gis_file_3hr
			#	print gis_file_1day
			
			files.append(gis_file_3hr )
			files.append(gis_file_3hr_tfw)
			
			#files.append(gis_file_1day )
			#files.append(gis_file_1day_tfw)
				
			startTime 	+= datetime.timedelta(hours=3)
		
	downloaded_files = get_early_gpm_files(files)
		
	for f in downloaded_files:
		try:
			if f.index(".3hr.tif"):
				arr 	= f.split("-")
				arr2	= arr[2].split(".")
				arr3	= arr[4].split(".")
				ymd		= arr2[4]
				gpm_dir	= os.path.join(config.data_dir, "gpm", ymd)
						
				process(gpm_dir, "gpm_3hrs", f, ymd+"."+arr3[0][1:])
		except ValueError:
			pass

		#try:
		#	if f.index(".1day.tif"):
		#		arr 	= f.split("-")
		#		arr2	= arr[2].split(".")
		#		arr3	= arr[4].split(".")
		#		ymd		= arr2[4]
		#		gpm_dir	= os.path.join(config.data_dir, "gpm", ymd)
						
		#		process(gpm_dir, "gpm_3hrs_1day", f, ymd+"."+arr3[0][1:])
		#except ValueError:
		#	pass
			
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

def cleanup(product_name):
	_dir			=  os.path.join(config.data_dir, product_name)
	cleanupdir(_dir, product_name)

#	
# ===============================
# Main
#
# python gpm_global.py --date 2015-04-07 -v -f

if __name__ == '__main__':

	global hexColors, levels
	
	aws_access_key 			= os.environ.get('AWS_ACCESSKEYID')
	aws_secret_access_key 	= os.environ.get('AWS_SECRETACCESSKEY')
	assert(aws_access_key)
	assert(aws_secret_access_key)
	
	parser = argparse.ArgumentParser(description='Generate GPM Rainfall Accumulation Products')
	apg_input = parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="forces products to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose on/off")
	apg_input.add_argument("-d", "--date", help="--date 2015-03-20 or today if not defined")
	apg_input.add_argument("-t", "--timespan", help="-timespan 1day| 3day | 7day | 3hrs | 30mn")

	#todaystr	= date.today().strftime("%Y-%m-%d %H:%M:%S")
	
	todaystr	=  datetime.datetime.utcnow()
	
	options 	= parser.parse_args()
	
	dt			= options.date or str(todaystr)
	force		= options.force
	verbose		= options.verbose
	timespan	= options.timespan or "1day"
	
	if timespan=="1day": 
		product_name = "gpm_1d"
	
	if timespan=="3day":
		product_name = "gpm_3d"
	
	if timespan=="7day":
		product_name = "gpm_7d"
	
	if timespan=="30mn":
		product_name = "gpm_30mn"
	
	if timespan=="3hrs":
		product_name = "gpm_3hrs"
		
	basedir 	= os.path.dirname(os.path.realpath(sys.argv[0]))
	
	today		= parse(dt)
	year		= today.year
	month		= today.month
	day			= today.day
	doy			= today.strftime('%j')
	ymd 		= "%d%02d%02d" % (year, month, day)		
		
	if verbose:
		print "Generate GPM Rainfall Products", timespan, dt
		
	gpm_dir	= os.path.join(config.data_dir, product_name, ymd)
	if not os.path.exists(gpm_dir):
	    os.makedirs(gpm_dir)
		
	region				= config.regions['global']
	s3_folder			= os.path.join(product_name, str(year), doy)
	s3_bucket			= region['bucket']
	
	gis_file_day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.1day.tif"%(year, month, day)
	gis_file_day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.1day.tfw"%(year, month, day)

	gis_file_3day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.3day.tif"%(year, month, day)
	gis_file_3day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.3day.tfw"%(year, month, day)

	gis_file_7day		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.7day.tif"%(year, month, day)
	gis_file_7day_tfw 	= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S233000-E235959.1410.V03E.7day.tfw"%(year, month, day)
	
	files 				= [
		gis_file_day, gis_file_day_tfw, 
		gis_file_3day, gis_file_3day_tfw, 
		gis_file_7day, gis_file_7day_tfw
	]
	
	# 12 colors
	hexColors     		= [ "#c0c0c0", "#018414","#018c4e","#02b331","#57d005","#b5e700","#f9f602","#fbc500","#FF9400","#FE0000","#C80000","#8F0000"]	
	
	if timespan == '1day':
		levels 				= [ 987, 610, 377, 233, 144, 89, 55, 34, 21, 13, 8, 5]
		if force or not os.path.exists(os.path.join(gpm_dir,gis_file_day)):
			print "get", gis_file_day, gis_file_day_tfw
			get_late_gpm_files([gis_file_day, gis_file_day_tfw], product_name)
		process(gpm_dir, "gpm_1d", gis_file_day, ymd)
		#execute( "rm %s %s" % (os.path.join(gpm_dir,gis_file_day), os.path.join(gpm_dir,gis_file_day_tfw)))
		
	if timespan == '3day':
		levels 				= [ 2584, 1597, 987, 610, 377, 233, 144, 89, 55, 34, 21, 13]
		if force or not os.path.exists(os.path.join(gpm_dir,gis_file_3day)):
			get_late_gpm_files([gis_file_3day, gis_file_3day_tfw], product_name)
		process(gpm_dir, "gpm_3d", gis_file_3day, ymd)
		#execute( "rm %s %s" % (os.path.join(gpm_dir,gis_file_3day), os.path.join(gpm_dir,gis_file_3day_tfw)))
		
	if timespan == '7day':
		levels 				= [ 2584, 1597, 987, 610, 377, 233, 144, 89, 55, 34, 21, 13]
		if force or not os.path.exists(os.path.join(gpm_dir,gis_file_7day)):
			get_late_gpm_files([gis_file_7day, gis_file_7day_tfw], product_name)
		process(gpm_dir, "gpm_7d", gis_file_7day, ymd)
		#execute( "rm %s %s" % (os.path.join(gpm_dir,gis_file_7day), os.path.join(gpm_dir,gis_file_7day_tfw)))
	
	# We will check the last 24hrs from given date or today (now)
	yesterday				= today - timedelta(hours=24)
	
	if timespan == '3hrs':
		levels 				= [ 610, 377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3]
		process_3hrs_files(gpm_dir, yesterday)
		
	if timespan == '30mn':
		levels 				= [ 233, 144, 89, 55, 34, 21, 13, 8, 5, 3, 2, 1]
		process_30mn_files(gpm_dir, yesterday)
		
	cleanup(product_name)	



	