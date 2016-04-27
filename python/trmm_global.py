#
# Rewrite of TRMM Regional processing
#

# Requirements:
#	gdal, numpy pytrmm...
#
import numpy, sys, os, inspect, math
from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, datetime, timedelta
from dateutil.parser import parse

from pytrmm import TRMM3B42RTFile

# Site configuration
import config
import argparse
from browseimage import MakeBrowseImage 
from s3 import CopyToS3
import json

ftp_site 	= "trmmopen.gsfc.nasa.gov"
path	 	= "pub/merged/3B42RT/"
gis_path 	= "pub/gis/"
force		= 0
verbose		= 0

def execute(cmd):
	if(verbose):
		print cmd

	os.system(cmd)

def CreateLevel(l, geojsonDir, fileName, src_ds, data, attr):
	global force, verbose
		
	projection  		= src_ds.GetProjection()
	geotransform		= src_ds.GetGeoTransform()
	#band				= src_ds.GetRasterBand(1)
		
	print geotransform
	
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

		cmd = str.format("potrace -i -z black -a 1.5 -t 3 -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", fileName+".geojson", fileName+".pgm", pres, xorg, ymax ); 
		execute(cmd)

		#cmd = str.format("node set_geojson_property.js --file {0} --prop frost={1}", fileName+".geojson", frost)
		#execute(cmd)
	
		#cmd = str.format("topojson -o {0} --simplify-proportion 0.5 -p {3}={1} -- {3}={2}", fileName+".topojson", l, fileName+".geojson", attr ); 
		cmd = str.format("topojson -q -o {0} --no-stitch-poles -p {3}={1} -- {3}={2}", fileName+".topojson", l, fileName+".geojson", attr ); 
		execute(cmd)
	
		# convert it back to json
		cmd = "topojson-geojson --precision 3 -o %s %s" % ( geojsonDir, fileName+".topojson" )
		execute(cmd)
	
		# rename file
		output_file = "%s_level_%d.geojson" % (attr, l)
		json_file	= "%s.json" % attr
		cmd 		= "mv %s %s" % (os.path.join(geojsonDir,json_file), os.path.join(geojsonDir, output_file))
		execute(cmd)

class TRMM:
	def __init__( self, dt, force, verbose ):
		arr 					= dt.split("-")

		self.year				= int(arr[0])
		self.month				= int(arr[1])
		self.day				= int(arr[2])
		
		self.ymd 				= "%d%02d%02d" % (self.year, self.month, self.day)		
		self.force				= force
		self.verbose			= verbose

		today					= parse(dt)
		self.doy				= today.strftime('%j')

		gis_file_day 			= "3B42RT.%04d%02d%02d21.7.1day.tif"%(self.year, self.month, self.day)
		gis_file_day_tfw 		= "3B42RT.%04d%02d%02d21.7.1day.tfw"%(self.year, self.month, self.day)

		self.trmm_gis_files 	= [gis_file_day, gis_file_day_tfw]

		# required directories
		self.trmm_3B42RT_dir	=  os.path.join(config.data_dir,"trmm","3B42RT", self.ymd)
		self.trmm_global_dir	=  os.path.join(config.data_dir,"trmm","global", self.ymd)

		self.trmm_dir			=  os.path.join(config.data_dir,"trmm", self.ymd)

		# Set file vars
		self.delete_files 		= os.path.join(self.trmm_dir, "TMP*")
	
		self.output_file_180	= os.path.join(self.trmm_dir, "trmm_24_%s_180.tif" % self.ymd)
		self.rgb_output_file 	= os.path.join(self.trmm_dir, "trmm_24_%s_rgb.tif"% self.ymd)

		self.color_file 		= os.path.join("cluts", "green-blue-gr.txt")

	# ======================================================================
	# Make sure directories exist
	#
	def checkdirs(self):

		if not os.path.exists(self.trmm_global_dir):
		    os.makedirs(self.trmm_global_dir)
	
		if not os.path.exists(self.trmm_dir):
		    os.makedirs(self.trmm_dir)


	# ===============================================================
	# Get TRMM daily files from that day at 21:00
	#			
	def get_daily_trmm_file(self):
		#filepath = path+str(self.year)
		filepath = gis_path+ "%d%02d" % (self.year,self.month)
	
		if verbose:
			print("Checking "+ftp_site+"/" + filepath + " for latest file...")
	
		try:
			ftp = FTP(ftp_site)
	
			ftp.login()               					# user anonymous, passwd anonymous@
			ftp.cwd(filepath)
	
		except Exception as e:
			print "FTP login Error", sys.exc_info()[0], e
		
			# Try alternate
			try:
				print "Try alternate", gis_path
				filepath = gis_path
				ftp.cwd(filepath)
			except Exception as e:
				print "Exception", e
				sys.exit(-1)

		#print self.trmm_gis_files
		for f in self.trmm_gis_files:
			if verbose:
				print "Trying to download", f
			
			local_filename = os.path.join(self.trmm_3B42RT_dir, f)
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
		
	# ===============================================================
	# Process All TRMM files from that day to get 24hr accumulation
	#
	def	process_trmm_file(self):
		self.generate_24h_accumulation()
		mydir			=  os.path.join(config.data_dir,"trmm")
		
		self.process(mydir, "trmm_24", self.output_file_180, ymd)

	#
	# We got from FTP the daily file in 10th of mm of accumulation
	#
	def generate_24h_accumulation(self):		
		if force or not os.path.exists(self.output_file_180):
			fname 	= os.path.join(self.trmm_3B42RT_dir, self.trmm_gis_files[0])
			#print "reading", fname

			ds 		= gdal.Open(fname)
			driver 	= gdal.GetDriverByName("GTiff")
			out_ds	= driver.CreateCopy( self.output_file_180, ds, 0)
			out_ds 	= None
			ds 		= None
		
		if force or (verbose and not os.path.exists(self.rgb_output_file)):	
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % (self.output_file_180, self.color_file, self.rgb_output_file)
			execute(cmd)

	def process(self, mydir, name, gis_file_day, ymd ):
		global force, verbose

		regionName = 'global'
	
		region_dir	= os.path.join(mydir,regionName, ymd)
		if not os.path.exists(region_dir):            
			os.makedirs(region_dir)
	
		origFileName 		= gis_file_day
		ds 					= gdal.Open(origFileName)
		geotransform		= ds.GetGeoTransform()

		xorg				= geotransform[0]
		yorg  				= geotransform[3]
		pixelsize			= geotransform[1]
		xmax				= xorg + geotransform[1]* ds.RasterXSize
		ymax				= yorg - geotransform[1]* ds.RasterYSize
	
		bbox				= [xorg, ymax, xmax, yorg]
	
		supersampled_file	= os.path.join(region_dir, "%s.%s_x5.tif" % (name, ymd))

		if force or not os.path.exists(supersampled_file):
			cmd 			= "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -r cubicspline -co COMPRESS=LZW %s %s"%(pixelsize/5, pixelsize/5, bbox[0], bbox[1], bbox[2], bbox[3], origFileName, supersampled_file)
			execute(cmd)
	
		geojsonDir	= os.path.join(region_dir,"geojson_%s" % (name))
		if not os.path.exists(geojsonDir):            
			os.makedirs(geojsonDir)

		levelsDir	= os.path.join(region_dir,"levels_%s" % (name))
		if not os.path.exists(levelsDir):            
			os.makedirs(levelsDir)

		merge_filename 		= os.path.join(geojsonDir, "%s.%s.geojson" % (name, ymd))
		topojson_filename 	= os.path.join(geojsonDir, "..", "%s.%s.topojson" % (name,ymd))
		browse_filename 	= os.path.join(geojsonDir, "..", "%s.%s_browse.tif" % (name,ymd))
		subset_aux_filename = os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif.aux.xml" % (name, ymd))
		subset_filename 	= os.path.join(geojsonDir, "..", "%s.%s_small_browse.tif" % (name, ymd))
		
		#osm_bg_image		= os.path.join(geojsonDir, "..", "osm_bg.png")
		osm_bg_image		= os.path.join(config.data_dir, "trmm", "global", "osm_bg.png")
		
		sw_osm_image		= os.path.join(geojsonDir, "..", "%s.%s_thn.jpg" % (name, ymd))
		tif_image			= os.path.join(geojsonDir, "..", "%s.%s.tif" % (name, ymd))

		geojson_filename 	= os.path.join(geojsonDir, "..", "%s.%s.json" % (name,ymd))

		levels 				= [377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3, 2]
		
		# http://hclwizard.org/hcl-color-scheme/
		# http://vis4.net/blog/posts/avoid-equidistant-hsv-colors/
		# from http://tristen.ca/hcl-picker/#/hlc/12/1/241824/55FEFF
		# Light to dark
		hexColors 			= [ "#56F6FC","#58DEEE","#5BC6DE","#5EAFCC","#5E99B8","#5D84A3","#596F8D","#535B77","#4A4861","#3F374B","#322737","#241824"]
	
		ds 					= gdal.Open( supersampled_file )
		band				= ds.GetRasterBand(1)
		data				= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize )

		sdata 				= data/10			# back to mm
	
		if force or not os.path.exists(topojson_filename+".gz"):
			for l in levels:
				fileName 	= os.path.join(levelsDir, ymd+"_level_%d.tif"%l)
				CreateLevel(l, geojsonDir, fileName, ds, sdata, "precip")
	
			jsonDict = dict(type='FeatureCollection', features=[])
	
			for l in reversed(levels):
				fileName 	= os.path.join(geojsonDir, "precip_level_%d.geojson"%l)
				if os.path.exists(fileName):
					with open(fileName) as data_file:    
						jdata = json.load(data_file)
		
					if 'features' in jdata:
						for f in jdata['features']:
							jsonDict['features'].append(f)
	

			with open(merge_filename, 'w') as outfile:
			    json.dump(jsonDict, outfile)	

			# Convert to topojson
			cmd 	= "topojson -p precip -o "+ topojson_filename + " " + merge_filename
			execute(cmd)

			cmd 	= "gzip --keep "+ topojson_filename
			execute(cmd)
		
		# problem is that we need to scale it or adjust the levels for coloring (easier)
		adjusted_levels 	= [3770, 2330, 1440, 890, 550, 340, 210, 130, 80, 50, 30, 20]
	
		zoom 	= 1
		scale 	= 1	
		bbox = [-179.999997, 66.5132592475, 180, -66.5132616387]	# for the bbox because we are using the GPM background image so we can compare
		
		if force or not os.path.exists(sw_osm_image):
			MakeBrowseImage(ds, browse_filename, subset_filename, osm_bg_image, sw_osm_image, adjusted_levels, hexColors, 1, 1, zoom, scale, bbox)
	
		if force or not os.path.exists(tif_image):
			cmd 			= "gdalwarp -overwrite -q -co COMPRESS=LZW %s %s"%( origFileName, tif_image)
			execute(cmd)
		
		ds = None
	
		file_list = [ sw_osm_image, topojson_filename+".gz", tif_image ]
		CopyToS3( s3_bucket, s3_folder, file_list, force, verbose )
	
		if not verbose: # Cleanup
			cmd = "rm -rf %s %s %s %s %s %s %s %s %s %s" % (origFileName, supersampled_file, merge_filename, topojson_filename, subset_aux_filename, browse_filename, subset_filename, osm_bg_image, geojsonDir, levelsDir)
			execute(cmd)
			

	
# python trmm_global.py --date 2015-08-11 -v
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)

	parser 		= argparse.ArgumentParser(description='TRMM Rainfall Processing')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", 	action='store_true', help="Forces new product to be generated")
	apg_input.add_argument("-v", "--verbose",	action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", 		help="date")
	
	todaystr	= date.today().strftime("%Y-%m-%d")
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	dt			= options.date or todaystr
	today		= parse(dt)
	year		= today.year
	month		= today.month
	day			= today.day
	doy			= today.strftime('%j')
	ymd 		= "%d%02d%02d" % (year, month, day)		
		
	region		= config.regions['global']
	s3_folder	= os.path.join("trmm_24", str(year), doy)
	s3_bucket	= region['bucket']
	
	app 		= TRMM( dt, force, verbose)
	
	app.checkdirs()
	app.get_daily_trmm_file()
	app.process_trmm_file()
	
	if verbose:
		print "Done."