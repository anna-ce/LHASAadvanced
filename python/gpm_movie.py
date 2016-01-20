#!/usr/bin/env python
#
# Created on 01/14/2016 Pat Cappelaere - Vightel Corporation
#
#
# GPM Movie
# 
#
import datetime
from datetime import date, timedelta
from dateutil.parser import parse

import logging

# Site configuration
import config
import argparse
import tempfile, os, glob,sys

from ftplib import FTP
from browseimage import mapbox_image, wms, Gen_bbox

import multiprocessing

# Need Pillow
# $ pip install Pillow
# Pillow in /usr/local/lib/python2.7/site-packages

from PIL import Image, ImageDraw, ImageFont
import textwrap
from which import *

force 		= 0
verbose 	= 0
ftp_site 	= "jsimpson.pps.eosdis.nasa.gov"
gis_path 	= "/data/imerg/gis/"
user		= 'pat@cappelaere.com'
password	= 'pat@cappelaere.com'

def execute( cmd ):
	if verbose:
		logger.debug(cmd)
	os.system(cmd)

def multiprocessing_download(filepath, local_filename):
	ftp = FTP(ftp_site)
	ftp.login(user, password)               					# user anonymous, passwd anonymous@
	ftp.cwd(filepath)

	f 	= os.path.basename(local_filename)
	err = 0
	
	if not os.path.exists(local_filename):
		logger.info("Trying to Download...%s", f)
		file = open(local_filename, 'wb')
		try:
			ftp.retrbinary("RETR " + f, file.write)
			file.close()
			
			# Make .tfw file rather than downloading it via ftp.... grrrr
			tfw_filename 	= local_filename.replace(".tif", ".tfw")
			tfwfile 		= open(tfw_filename, 'w')
			tfw_str =  "       0.1000000\n"
			tfw_str += "       0.0000000\n"
			tfw_str += "       0.0000000\n"
			tfw_str += "      -0.1000000\n"
			tfw_str += "    -179.9499969\n"
			tfw_str += "      89.9499969\n"
			tfwfile.write(tfw_str)
			tfwfile.close()
		
		except Exception as e:
			print "GPM IMERG FTP Error", sys.exc_info()[0], e					
			os.remove(local_filename)
			err = 1
	
	ftp.close()
	return err
	
#	
# Download all 30mn files for that day in monthly directory
#
def download_gpm_files(files, mydir, year, month):	
	filepath = gis_path+ "%02d" % ( month)
	
	pool 	= multiprocessing.Pool(processes=processes)

	local_filenames = map(lambda x: os.path.join(mydir, x), files)
	
	for f in local_filenames:
		pool.apply_async(multiprocessing_download, args=(filepath, f, ))
	
	pool.close()
	pool.join()
	
def get_30mn_files(mydir, year, month, day, ymd):
	startTime 	= datetime.datetime(year,month,day)
	minute 		= 0
	files		= []
	today		= datetime.datetime.now()
	
	while minute<1440:
		sh 	= startTime.hour
		sm	= startTime.minute
		ss	= startTime.second
		em	= sm + 29
		
		dt					= datetime.datetime(year, month, day, sh, em, 0)
		gis_file_30mn 		= "3B-HHR-L.MS.MRG.3IMERG.%d%02d%02d-S%02d%02d00-E%02d%d59.%04d.V03E.30min.tif"%(year, month, day,sh,sm,sh,em,minute)
		
		files.append(gis_file_30mn)
		
		minute += 30
		startTime += datetime.timedelta(minutes=30)
		
	download_gpm_files(files, mydir, year, month)
		
def cleanup():
	cmd = str.format("rm {0}/*.30mn.* {0}/*.jpg", outputDir )
	execute(cmd)
	
def make_movie():
	logger.info("Making Movie...")
	movie_filename = os.path.join(outputDir, "movie.mp4")

	if force or not os.path.isfile(movie_filename):				
		#cmd = str.format("ffmpeg -f image2 -i {0}/%06d.jpg {1}", outputDir, movie_filename)
		cmd = str.format("convert -quality 100 {0}/*.jpg {1}", outputDir, movie_filename)
		execute(cmd)
	
	#cleanup()

def annotate(idx, blend_filename, timestamp):
	basename		= os.path.basename(blend_filename)
	dirname			= os.path.dirname(blend_filename)
	
	filename		= "%06d.jpg" % idx
	
	annotated_filename 	= os.path.join(outputDir, filename)
	
	try:
		if force or not os.path.isfile(annotated_filename):	

			logger.debug( "annotating: %s from %s", annotated_filename, blend_filename)
		
			im				= Image.open(blend_filename).convert('RGB')
			draw			= ImageDraw.Draw(im)
			text			= timestamp
			font_file   	= os.path.join(defaultDir, "pilfonts", "timR10.pil")
			font 			= ImageFont.load(font_file)
			fontsize		= 10
	
			xoff			= int(width/2 - len(timestamp))
			yoff			= int(height - 50)
	
			#print "drawing text", xoff, yoff, timestamp
			draw.text((xoff, yoff),timestamp, font=font, fill=(0,0,0,255))
	
			im.save(annotated_filename)
			add_legend(annotated_filename)
	
			logger.debug( "annotated: %s", annotated_filename)

	except Exception as e:
		print e
	
		
def add_legend(filename):
	logger.debug( "add_legend: %s", filename)
	gpm_colors_png = os.path.join(defaultDir, "cluts", "gpm_colors.png")
	cmd = str.format("convert {0} {1} -gravity East -composite {2}", filename, gpm_colors_png, filename)
	execute(cmd)
	
def blend_with_map( idx, rgb_filename, osm_bg_image ):
	basename		= os.path.basename(rgb_filename)
	blend_filename 	= rgb_filename.replace(".rgb.tif", ".blend.png")
	
	if force or not os.path.isfile(blend_filename):	
		loggind.degug("blend: %s", rgb_filename, osm_bg_image)

		cmd = str.format("composite -quiet -gravity center -blend 60 {0} {1} {2}", rgb_filename, osm_bg_image, blend_filename)
		execute(cmd)
	
	arr 		= basename.split(".")
	timestamp 	= arr[4]
	
	annotate(idx, blend_filename, timestamp)
	
def colorize(idx, subset_filename):
	rgb_filename 	= subset_filename.replace(".subset.tif", ".rgb.tif")

	color_file		= os.path.join(defaultDir, "cluts", "gpm_colors.txt")

	if not os.path.exists(rgb_filename):	
		logger.debug("colorize to: %s", rgb_filename)
		
		cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( subset_filename, color_file, rgb_filename)
		execute(cmd)
		
	blend_with_map( idx, rgb_filename, osm_bg_image )

def subset_file(idx, filename):
	basename		= os.path.basename(filename)
	dirname			= os.path.dirname(filename)
	
	subset_filename = os.path.join(outputDir, basename.replace(".tif", ".subset.tif"))
	
	if force or not os.path.exists(subset_filename):
		logger.debug("subset to: %s", subset_filename)

		xmin 	= ullon
		if lrlat > ullat:
			ymin = ullat 
		else: 
			ymin = lrlat
			
		xmax	= lrlon
		
		if lrlat > ullat:
			ymax = lrlat 
		else: 
			ymax = ullat
		
		cmd 			= "gdalwarp -overwrite -q -ts %d %d -te %f %f %f %f -r cubicspline -co COMPRESS=LZW %s %s"%(width, height, xmin, ymin, xmax, ymax, filename, subset_filename)
		execute(cmd)
		
	colorize(idx, subset_filename)
	
def process_file(filename):
	subset_file(filename)
	
def worker_process_file(idx, filename):
	subset_file(idx, filename)
	return 1

def process_files(gpm_dir, prefix):	
	#queue 			= multiprocessing.Queue()
	pool 			= multiprocessing.Pool(processes=processes)
	#processed_files = 0

	pathname 		= os.path.join(gpm_dir, prefix)
	files 			= glob.glob(pathname)
	
	logger.info("Processing files...")
	results = [pool.apply_async(worker_process_file, args=(idx,f)) for idx,f in enumerate(files)]
	pool.close()
	pool.join()

	#make_movie()
	
#
# ======================================================================
#	python gpm_movie.py --startTime 2016-01-12 --endTime 2016-01-15 --zoom 7 --lat -20.6332733 --lon -42.0 --outputDir ../tmp/tmpkq9U7I -v
#
if __name__ == '__main__':
	
	parser 		= argparse.ArgumentParser(description='MODIS Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", 	action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", 	action='store_true', help="Verbose Flag")
	apg_input.add_argument("--startTime", 		help="startTime", 	required=1)
	apg_input.add_argument("--endTime", 		help="endTime", 	required=1)
	apg_input.add_argument("--lat", 			help="latitude", 	required=1)
	apg_input.add_argument("--lon", 			help="longitude", 	required=1)
	apg_input.add_argument("--zoom", 			help="longitude", 	required=1)
	apg_input.add_argument("--outputDir", 		help="longitude", 	required=1)
	apg_input.add_argument("--processes", 		help="Number of concurrent processes", 	default=multiprocessing.cpu_count())
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	processes	= options.processes
	
	logging.basicConfig(format='%(asctime)s %(message)s')
	logger 		= logging.getLogger();
	if verbose:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)
		
	prog		= sys.argv[0]
	defaultDir	= os.path.dirname(prog)
	
	logger.debug("processes %d", processes)
	
	#todaystr	= date.today().strftime("%Y-%m-%d")
	#dt			= options.date or todaystr
	#today		= parse(dt)
	#year		= today.year
	#month		= today.month
	#day		= today.day
	#doy		= today.strftime('%j')
	#ymd 		= "%d%02d%02d" % (year, month, day)		

	startTime	= parse(options.startTime)
	endTime		= parse(options.endTime)

	year		= startTime.year
	month		= startTime.month
	day			= startTime.day
	doy			= startTime.strftime('%j')
	ymd 		= "%d%02d%02d" % (year, month, day)		
	
	#
	# Make sure we have ffmpeg & ImageMagick installed
	#
	# confirm_availability_of("ffmpeg")
	confirm_availability_of("convert")
	confirm_availability_of("gdalwarp")
	confirm_availability_of("gdaldem")
	confirm_availability_of("composite")

	color_file		= os.path.join(defaultDir, "cluts", "gpm_colors.txt")
	if not os.path.exists(color_file):
		logger.error( "Cannot find color file %s", color_file)
		sys.exit(-1)
		
	centerlat 		= float(options.lat)
	centerlon		= float(options.lon)
	z				= int(options.zoom)
	
	if centerlon < -180 or centerlon > 180:
		logger.error("Invalid longitude %f", centerlon)
		sys.exit(-1)
		
	if centerlat < -90 or centerlat > 90:
		logger.error("Invalid latitude %f", centerlat)
		sys.exit(-1)
	
	if z < 3 or z > 12:
		logger.error("Invalid zoom level %d", z )
		sys.exit(-1)

	outputDir		= options.outputDir
		
	logger.info ("gpm_movie.py starTime: %s endTime: %s zoom: %s, lat: %f lon: %f outputDir: %s", startTime , endTime, z, centerlat, centerlon, outputDir)
			
	goldenratio		= 1.618
	height			= 610
	width			= 1024
		
	if not os.path.exists(outputDir):
		os.mkdir(outputDir)
		
	osm_bg_image	= os.path.join(outputDir, "mapbox_map.png")
		
	# Let's generate a map background
	if force or not os.path.exists(osm_bg_image):
		mapbox_image(centerlat, centerlon, z, width, height, osm_bg_image)
		
	ullon, ullat, lrlon, lrlat = Gen_bbox(centerlat, centerlon, z, width, height)
		
	#
	# Let's make sure we have all the files one day at a time
	#
	done = 0
	logger.info("Checking GPM files availability...")
	while not done:
		get_30mn_files(outputDir, year, month, day, ymd)
		startTime += timedelta(days=1)
		if( startTime > endTime):
			done = 1
		else:
			year		= startTime.year
			month		= startTime.month
			day			= startTime.day
			doy			= startTime.strftime('%j')
			ymd 		= "%d%02d%02d" % (year, month, day)		
			
	
	#ftp.close()
	
	# Let's find process the files
	process_files(outputDir, "3B-HHR-L.MS.MRG.3IMERG.*.V03E.30min.tif")
	logger.info("Done")