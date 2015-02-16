#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
import numpy, sys, os, inspect, math
from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, datetime, timedelta

from pytrmm import TRMM3B42RTFile

# Site configuration
import config
import argparse

ftp_site 	= "trmmopen.gsfc.nasa.gov"
path	 	= "pub/merged/3B42RT/"
gis_path 	= "pub/gis/"
force		= 0
verbose		= 0

class TRMM:
	def __init__( self, dt, force, verbose ):
		arr 			= dt.split("-")
		
		self.year			= int(arr[0])
		self.month			= int(arr[1])
		self.day			= int(arr[2])
	
		
		self.ymd 			= "%d%02d%02d" % (self.year, self.month, self.day)		
		self.force			= force
		self.verbose		= verbose

		gis_file_00 		= "3B42RT.%04d%02d%02d00.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_03 		= "3B42RT.%04d%02d%02d03.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_06 		= "3B42RT.%04d%02d%02d06.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_09 		= "3B42RT.%04d%02d%02d09.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_12 		= "3B42RT.%04d%02d%02d12.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_15 		= "3B42RT.%04d%02d%02d15.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_18 		= "3B42RT.%04d%02d%02d18.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_21 		= "3B42RT.%04d%02d%02d21.7.03hr.tif"%(self.year, self.month, self.day)
		gis_file_day 		= "3B42RT.%04d%02d%02d21.7.1day.tif"%(self.year, self.month, self.day)
		gis_file_day_tfw 	= "3B42RT.%04d%02d%02d21.7.1day.tfw"%(self.year, self.month, self.day)
	
		#self.trmm_files 	= [file_00, file_03, file_06, file_09, file_12, file_15, file_18, file_21]
		#self.trmm_gis_files = [gis_file_00, gis_file_03, gis_file_06, gis_file_09, gis_file_12, gis_file_15, gis_file_18, gis_file_21, gis_file_day, gis_file_day_tfw]
		self.trmm_gis_files = [gis_file_day, gis_file_day_tfw]

		# required directories
		self.trmm_3B42RT_dir	=  os.path.join(config.data_dir,"trmm","3B42RT", self.ymd)
		self.trmm_d02_dir		=  os.path.join(config.data_dir,"trmm","d02", self.ymd)
		self.trmm_d03_dir		=  os.path.join(config.data_dir,"trmm","d03", self.ymd)
		self.trmm_dir			=  os.path.join(config.data_dir,"trmm", self.ymd)

		# Set file vars
		self.delete_files 		= os.path.join(self.trmm_dir, "TMP*")
		#self.output_file_360	= os.path.join(self.trmm_dir, "TMP_trmm_24_%s_360.tif" % self.ymd)
		self.output_file_360	= os.path.join(self.trmm_3B42RT_dir, "trmm_24_%s_180.tif" % self.ymd)
		self.output_file_180	= os.path.join(self.trmm_dir, "trmm_24_%s_180.tif" % self.ymd)
		self.output_file_180_1	= os.path.join(self.trmm_dir, "TMP_trmm_24_%s_180_1.tif" % self.ymd)
		self.output_file_180_2	= os.path.join(self.trmm_dir, "TMP_trmm_24_%s_180_2.tif" % self.ymd)
		self.rgb_output_file 	= os.path.join(self.trmm_dir, "trmm_24_%s_rgb.tif"% self.ymd)

		self.color_file 		= os.path.join("cluts", "green-blue-gr.txt")


	def execute(self, cmd):
		if(self.verbose):
			print cmd
		os.system(cmd)
	
	# ===============================================================
	# Get TRMM daily files from that day at 21:00
	#			
	def get_daily_trmm_files(self):
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

		print self.trmm_gis_files
		for f in self.trmm_gis_files:
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

	#
	# We got from FTP the daily file in 10th of mm of accumulation
	#
	def generate_24h_accumulation(self):		
		if force or not os.path.exists(self.output_file_180):
			
			fname 	= os.path.join(self.trmm_3B42RT_dir, self.trmm_gis_files[0])
			print "reading", fname

			ds 		= gdal.Open(fname)
			driver 	= gdal.GetDriverByName("GTiff")
			out_ds	= driver.CreateCopy( self.output_file_180, ds, 0)
			out_ds 	= None
			ds 		= None
			
		if force or (verbose and not os.path.exists(self.rgb_output_file)):	
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( self.output_file_180, self.color_file, self.rgb_output_file)
			self.execute(cmd)
	
	def process_trmm_region_subset(self, global_file, bbox, subset_file, clut_file, rgb_subset_file):
		if force or not os.path.exists(subset_file):
			cmd = "gdalwarp -overwrite -q -te %f %f %f %f %s %s" % (bbox[0], bbox[1], bbox[2], bbox[3], global_file, subset_file)
			self.execute(cmd)
		
		if force or not os.path.exists(rgb_subset_file):
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( subset_file, clut_file, rgb_subset_file)
			self.execute(cmd)
	
		if force or (verbose and not os.path.exists(self.rgb_output_file)):	
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( self.output_file_180, self.color_file, self.rgb_output_file)
			self.execute(cmd)
	
	
	def process_trmm_region_upsample(self, pixelsize, bbox, global_file, resampled_file, resampled_rgb_file):
		if force or not os.path.exists(resampled_file):
			print "pixelsize", pixelsize
			
			cmd = "gdalwarp -overwrite -q -tr %s %s -te %f %f %f %f -co COMPRESS=LZW %s %s" % (str(pixelsize), str(pixelsize), bbox[0], bbox[1], bbox[2], bbox[3], global_file, resampled_file)
			self.execute(cmd)
			
		if force or (verbose and not os.path.exists(resampled_rgb_file)):
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( resampled_file, self.color_file, resampled_rgb_file)
			self.execute(cmd)
	
	def process_trmm_region_thumbnail(self, rgb_subset_file, thn_width, thn_height, static_file,  thumbnail_file):
		tmp_file = thumbnail_file + ".tmp.tif"
		if force or not os.path.exists(thumbnail_file):
			cmd="gdalwarp -overwrite -q -multi -ts %d %d -r cubicspline -co COMPRESS=LZW %s %s" % (thn_width, thn_height, rgb_subset_file, tmp_file )
			self.execute(cmd)
			cmd = "composite -blend 60 %s %s %s" % ( tmp_file, static_file, thumbnail_file)
			self.execute(cmd)
			self.execute("rm "+tmp_file)
	
	
	def CreateTopojsonFile(self, fileName, src_ds, projection, geotransform, ct, data, pres, xorg, ymax, water ):
	
		driver 				= gdal.GetDriverByName( "GTiff" )
		dst_ds_dataset		= driver.Create( fileName, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte, [ 'COMPRESS=DEFLATE' ] )
		
		dst_ds_dataset.SetGeoTransform( geotransform )
		dst_ds_dataset.SetProjection( projection )

		o_band				= dst_ds_dataset.GetRasterBand(1)
	
		o_band.SetRasterColorTable(ct)
		o_band.WriteArray(data, 0, 0)

		dst_ds_dataset = None
		print "Created", fileName

		cmd = "gdal_translate -q -of PNM -expand gray " + fileName + " "+fileName+".bmp"
		self.execute(cmd)

		# -i  		invert before processing
		# -t 2  	suppress speckles of up to this many pixels. 
		# -a 1.5  	set the corner threshold parameter
		# -z black  specify how to resolve ambiguities in path decomposition. Must be one of black, white, right, left, minority, majority, or random. Default is minority
		# -x 		scaling factor
		# -L		left margin
		# -B		bottom margin

		cmd = str.format("potrace -i -z black -a 1.5 -t 3 -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", fileName+".geojson", fileName+".bmp", pres, xorg, ymax ); 
		self.execute(cmd)
	
		cmd = str.format("topojson -o {0} --simplify-proportion 0.75 -p precip={1} -- precip={2}", fileName+".topojson", water, fileName+".geojson" ); 
		self.execute(cmd)
	
		# convert it back to json
		cmd = "topojson-geojson --precision 4 -o %s %s" % ( self.geojsonDir, fileName+".topojson" )
		self.execute(cmd)
	
		# rename file
		output_file = "precip_%d.geojson" % water
		cmd = "mv %s %s" % (os.path.join(self.geojsonDir,"precip.json"), os.path.join(self.geojsonDir, output_file))
		self.execute(cmd)
		
	def process_trmm_region_topojson(self, dx, subset_file, supersampled_file, supersampled_rgb_file, pixelsize, bbox, shp_file, geojson_file, topojson_file, topojson_gz_file):
		# we need to resample even higher to improve resolution
		if force or not os.path.exists(supersampled_file):
			cmd = "gdalwarp -overwrite -q -tr %f %f -te %f %f %f %f -r cubicspline -co COMPRESS=LZW %s %s"%(pixelsize/10, pixelsize/10, bbox[0], bbox[1], bbox[2], bbox[3], subset_file, supersampled_file)
			self.execute(cmd)

		if force or (verbose and not os.path.exists(supersampled_rgb_file)):
			cmd = "gdaldem color-relief -q -alpha -of GTiff %s %s %s" % ( supersampled_file, self.color_file, supersampled_rgb_file)
			self.execute(cmd)

		src_ds 				= gdal.Open( supersampled_file )
		projection  		= src_ds.GetProjection()
		geotransform		= src_ds.GetGeoTransform()
		band				= src_ds.GetRasterBand(1)
		data				= band.ReadAsArray(0, 0, src_ds.RasterXSize, src_ds.RasterYSize )
		
		data /= 10			# back to mm
		
		xorg				= geotransform[0]
		yorg  				= geotransform[3]
		pres				= geotransform[1]
		xmax				= xorg + geotransform[1]* src_ds.RasterXSize
		ymax				= yorg - geotransform[1]* src_ds.RasterYSize

		levelsDir = os.path.join(config.data_dir,"trmm", dx, self.ymd,"levels" )
		if not os.path.exists(levelsDir):
			os.makedirs(levelsDir)
		
		self.geojsonDir		= os.path.join(config.data_dir,"trmm", dx, self.ymd, "geojson")
		if not os.path.exists(self.geojsonDir):
			os.makedirs(self.geojsonDir)
		
		# precipitation levels in 10th of mm
		levels = [1,2,3,5,8,13,21,34,55,89,144]
		ct = gdal.ColorTable()
		for i in range(256):
			ct.SetColorEntry( i, (255, 255, 255, 255) )
		ct.SetColorEntry( 0, (0, 0, 0, 255) )
					
		#for lev in enumerate(levels):
		for lev in levels:
			fileName = os.path.join(levelsDir, "level_"+str(lev)+".tif")
			for i in range(0,lev):
				ct.SetColorEntry( i, (0, 0, 0, 255) )
			
			self.CreateTopojsonFile(fileName, src_ds, projection, geotransform, ct, data, pres, xorg, ymax, lev )
		
		src_ds = None	
	
	def process_trmm_region_to_s3( self, dx, thumbnail_file, topojson_gz_file, tif_file):
		# copy mbtiles to S3
		region 		= config.regions[dx]
		bucketName 	= region['bucket']
		folder		= self.ymd
	 
		cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + self.ymd + " --file " + tif_file
		if verbose:
			cmd += " --verbose"
		#if force:
		cmd += " --force"
		
		self.execute(cmd)
	
		cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + self.ymd + " --file " + topojson_gz_file
		if verbose:
			cmd += " --verbose"
		#if force:
		cmd += " --force"
			
		self.execute(cmd)

		cmd = "./aws-copy.py --bucket " + bucketName + " --folder " + self.ymd + " --file " + thumbnail_file
		if verbose:
			cmd += " --verbose"
		#if force:
		cmd += " --force"
		self.execute(cmd)
	
	def process_trmm_region_cleanup(self, dx):
		if not verbose:			# probably debugging, so do not dispose of artifacts
			delete_files = [
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.dbf" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.geojson" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.prj" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.shp" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.shx" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km_rgb.tif" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_100m_rgb.tif" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_rgb.tif" % (dx,self.ymd)),
				#os.path.join(config.data_dir,"trmm", dx, ymd, "trmm_24_%s_%s_1km.tif" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s.topojson" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_100m.*" % (dx,self.ymd)),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "geojson"),
				os.path.join(config.data_dir,"trmm", dx, self.ymd, "levels")
			]
			cmd = "rm -rf "+ " ".join(delete_files)
			self.execute(cmd)
		
			if verbose:
				print "Removed files"
	
	# ===========================
	# Subset 24hr Rainfall Accumulation and resample for specific region
	#
	def process_trmm_region( self, dx ):
		region 		= config.regions[dx]
		bbox		= region['bbox']
		tzoom   	= region['tiles-zoom']
		pixelsize   = region['pixelsize']
		thn_width   = region['thn_width']
		thn_height  = region['thn_height']
		bucketName 	= region['bucket']
    
		if verbose:
			print "process_trmm_region:", dx, pixelsize

		subset_file 			= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s.tif" % (dx,self.ymd))
		thumbnail_file 			= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s.thn.png" % (dx,self.ymd))
		static_file 			= os.path.join(config.data_dir,"trmm", dx, "%s_static.tiff" % (dx))
		rgb_subset_file			= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_rgb.tif" % (dx,self.ymd))
		resampled_file 			= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.tif" % (dx,self.ymd))
		resampled_rgb_file 		= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km_rgb.tif" % (dx,self.ymd))
		supersampled_file	 	= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_100m.tif" % (dx,self.ymd))
		supersampled_rgb_file 	= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_100m_rgb.tif" % (dx,self.ymd))
		shp_file 				= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.shp" % (dx,self.ymd))
		geojson_file 			= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s_1km.geojson" % (dx,self.ymd))
		topojson_file			= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s.topojson" % (dx,self.ymd))
		topojson_gz_file		= os.path.join(config.data_dir,"trmm", dx, self.ymd, "trmm_24_%s_%s.topojson.gz" % (dx,self.ymd))

		self.process_trmm_region_subset(self.output_file_180, bbox, subset_file, self.color_file, rgb_subset_file)
	
		if force or not os.path.exists(resampled_file):
			self.process_trmm_region_subset(self.output_file_180, bbox, subset_file, self.color_file, rgb_subset_file)
			self.process_trmm_region_upsample(pixelsize, bbox, self.output_file_180, resampled_file, resampled_rgb_file)
			self.process_trmm_region_thumbnail( rgb_subset_file, thn_width, thn_height, static_file,  thumbnail_file)
		
		if force or not os.path.exists(topojson_gz_file):
			self.process_trmm_region_topojson( dx, subset_file, supersampled_file, supersampled_rgb_file, pixelsize, bbox, shp_file, geojson_file, topojson_file, topojson_gz_file )
	
			# merge the trmm files
			cmd = "node trmm_merge.js "+dx+ " " + self.ymd
			self.execute(cmd)
			
		self.process_trmm_region_to_s3( dx, thumbnail_file, topojson_gz_file, subset_file)
		
		self.process_trmm_region_cleanup(dx)
		
		
	# ===============================================================
	# Process All TRMM files from that day to get 24hr accumulation
	#
	def	process_trmm_files(self, region):
		self.generate_24h_accumulation()
		self.process_trmm_region(region)
	
	# ======================================================================
	# Make sure directories exist
	#
	def checkdirs(self):
		
		if not os.path.exists(self.trmm_3B42RT_dir):
		    os.makedirs(self.trmm_3B42RT_dir)

		if not os.path.exists(self.trmm_d02_dir):
		    os.makedirs(self.trmm_d02_dir)

		if not os.path.exists(self.trmm_d03_dir):
		    os.makedirs(self.trmm_d03_dir)
		
		if not os.path.exists(self.trmm_dir):
		    os.makedirs(self.trmm_dir)
#
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)

	parser 		= argparse.ArgumentParser(description='TRMM Rainfall Processing')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	apg_input.add_argument("-d", "--date", help="date")
	apg_input.add_argument("-r", "--region", help="region d02|d03")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	region		= options.region
	d			= options.date
		
	assert(config.regions[region])
	
	app = TRMM( d, force, verbose  )
	app.checkdirs()
	app.get_daily_trmm_files()
	app.process_trmm_files(region)
	
	if verbose:
		print "Done."