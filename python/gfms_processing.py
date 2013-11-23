#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
import numpy, sys, os, inspect, urllib
import argparse
import numpy

from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, timedelta

# Site configuration
import config

year 	= config.year
day	 	= config.day
ym		= config.ym

url		= "http://eagle1.umd.edu"

class GFMS:
	def __init__( self, inpath, force, verbose ):
		self.inpath 	= inpath
		self.force		= force
		self.verbose	= verbose
		
	def get_latest_file(self):
		path 			= "%s/flood/download/%s/%s/Flood_byStor_%s%02d00.bin" % (url, year, ym, ym, day)
		fname 			= "Flood_byStor_%s%02d00.bin" % (ym, day)
		fullname		= os.path.join(self.inpath, "gfms", fname)
		
		if not os.path.exists(fullname):
			if self.verbose:
				print "retrieving ", path, " -> ", fullname
			urllib.urlretrieve(path, fullname)
		
		self.process()
		
		
	def get_latest_highres_file(self):
		path 			= "%s/flood/download1km/%s/%s/Routed_%s%02d00.bin" % (url, year, ym, ym, day)
		fname 			= "Routed_%s%02d00.bin" % (ym, day)
		fullname		= os.path.join(self.inpath, "gfms", fname)
		
		def reporthook(blocks_read, block_size, total_size):
			if not blocks_read:
				print 'Connection opened'
				return
			if total_size < 0:
				# Unknown size
				print 'Read %d blocks' % blocks_read
			else:
				amount_read = blocks_read * block_size
				print 'Read %d blocks, or %d/%d' % (blocks_read, amount_read, total_size)
			return
					
		if not os.path.exists(fullname):
			if self.verbose:
				print "retrieving ", path, " -> ", fullname
			urllib.urlretrieve(path, fullname, reporthook)
		else:
			print "highres exists:", fullname

	def process_highres_region(self, dx, dt):
		region 				= config.regions[dx]
		bbox				= region['bbox']
		tzoom				= region['tiles-zoom']
		
		if self.verbose:
			print "gfms highres processing region:", dx, dt
			
		output_file			= os.path.join(self.inpath, "gfms", "Routed_%s%02d00.tif" % (ym, day))
		subset_file			= os.path.join(self.inpath, "gfms", "Routed_%s_subset_%s.tif" % (dt, dx))
		subset_rgb_file		= os.path.join(self.inpath, "gfms", "Routed_%s_subset_%s_rgb.tif" % (dt, dx))
		color_file			= os.path.join(self.inpath, "gfms_colors.txt")
		mbtiles_dir 		= os.path.join(config.data_dir,"mbtiles", "gfms_highres_%s_%s" % (dt, dx))
		mbtiles_fname 		= mbtiles_dir+".mbtiles"
		
		# subset it to our BBOX
		# use ullr
		if self.force or not os.path.exists(subset_file):
			lonlats	= "" + str(bbox[0]) + " " + str(bbox[3]) + " " + str(bbox[2]) + " " + str(bbox[1])	
			cmd 	= "gdal_translate -q -projwin " + lonlats +" "+ output_file+ " " + subset_file
			if verbose:
				print cmd
			os.system(cmd)
			
		if self.force or not os.path.exists(subset_rgb_file):		
			cmd = "gdaldem color-relief -q -alpha "+ subset_file + " " + color_file + " " + subset_rgb_file
			if self.verbose:
				print cmd
			os.system(cmd)

		# mbtiles
		if self.force or not os.path.exists(mbtiles_fname):		
			cmd = "./gdal2tiles.py -z "+ tzoom + " " + subset_rgb_file  + " " + mbtiles_dir
			if self.verbose:
				print cmd
			os.system(cmd)

			cmd = "./mb-util " + mbtiles_dir  + " " + mbtiles_fname
			if self.verbose:
				print cmd
			os.system(cmd)

		# copy mbtiles to S3
		if os.path.exists(mbtiles_fname):
			bucketName = region['bucket']
			cmd = "aws-copy.py --bucket "+bucketName+ " --file " + mbtiles_fname
			if self.verbose:
				cmd += " --verbose "
				print cmd
			os.system(cmd)

			cmd = "rm -rf "+ mbtiles_dir
			if verbose:
				print cmd
				os.system(cmd)
			
	def process_highres_d02(self, dt):
		self.process_highres_region("d02", dt)

	def process_highres_d03(self, dt):
		self.process_highres_region("d03", dt)
				
	def process_highres(self):
		input_fname 			= "Routed_%s%02d00.bin" % (ym, day)
		input_fullname			= os.path.join(self.inpath, "gfms", input_fname)
		output_fname 			= "Routed_%s%02d00.tif" % (ym, day)
		output_fullname			= os.path.join(self.inpath, "gfms", output_fname)
		output_rgb_fname		= "Routed_%s%02d00_rgb.tif" % (ym, day)
		output_rgb_fullname		= os.path.join(self.inpath, "gfms", output_rgb_fname)
		color_file				= os.path.join(self.inpath, "gfms_colors.txt")
		mbtiles_dir 			= os.path.join(config.data_dir,"mbtiles", "gfms_highres_%s%02d00" % (ym, day))
		mbtiles_fname 			= mbtiles_dir+".mbtiles"

		if self.force or not os.path.exists(output_fullname):		
			rows 	= 12001
			cols	= 36870
			size	= rows*cols
		
			fd		= open(input_fullname, 'rb')
			shape	= (rows, cols)
			data 	= numpy.fromfile(file=fd,dtype=numpy.float32, count=size).reshape(shape)

			print "stats:", data.size, data.min(), data.mean(), data.max(), data.std()

			x		= -127.2458335
			y		= 50.0001665
			res		= 0.00833
			nodata	= -9999
			

			# Create gtif
			driver = gdal.GetDriverByName("GTiff")
			dst_ds = driver.Create(output_fullname, cols, rows, 1, gdal.GDT_Float32)
			# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
			dst_ds.SetGeoTransform( [ x, res, 0, y, 0, -res ] )

			# set the reference info 
			srs = osr.SpatialReference()
			srs.ImportFromEPSG(4326)
			dst_ds.SetProjection( srs.ExportToWkt() )

			# write the band
			band = dst_ds.GetRasterBand(1)
			band.SetNoDataValue(nodata)
			band.WriteArray(data)
			dst_ds = None

		dt = "%s%02d00" %(ym,day)
		self.process_highres_d02(dt)
		self.process_highres_d03(dt)
			
	def process(self):
		input_fname 			= "Flood_byStor_%s%02d00.bin" % (ym, day)
		input_fullname			= os.path.join(self.inpath, "gfms", input_fname)
		output_fname 			= "Flood_byStor_%s%02d00.tif" % (ym, day)
		output_fullname			= os.path.join(self.inpath, "gfms", output_fname)
		output_rgb_fname		= "Flood_byStor_%s%02d00_rgb.tif" % (ym, day)
		output_rgb_fullname		= os.path.join(self.inpath, "gfms", output_rgb_fname)
		color_file				= os.path.join(self.inpath, "gfms_colors.txt")
		mbtiles_dir 			= os.path.join(config.data_dir,"mbtiles", "gfms_%s%02d00" % (ym, day))
		mbtiles_fname 			= mbtiles_dir+".mbtiles"

		region                  = config.regions['global']
		tzoom                   = region['tiles-zoom']
        
		if self.force or not os.path.exists(output_fullname):		
			rows 	= 800 
			cols	= 2458
			size	= rows*cols
			
			if verbose:
				print "gfms processing:", input_fullname
			
			fd		= open(input_fullname, 'rb')
			shape	= (rows, cols)
			data 	= numpy.fromfile(file=fd,dtype=numpy.float32, count=size).reshape(shape)
			
			#print "stats:", data.size, data.min(), data.mean(), data.max(), data.std()
			
			x		= -127.5
			y		= 50
			res		= 0.125
		
			# Create gtif
			driver = gdal.GetDriverByName("GTiff")
			dst_ds = driver.Create(output_fullname, cols, rows, 1, gdal.GDT_Float32)
			# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
			dst_ds.SetGeoTransform( [ x, res, 0, y, 0, -res ] )

			# set the reference info 
			srs = osr.SpatialReference()
			srs.ImportFromEPSG(4326)
			dst_ds.SetProjection( srs.ExportToWkt() )

			# write the band
			band = dst_ds.GetRasterBand(1)
			band.SetNoDataValue(-9999)
			band.WriteArray(data)
			dst_ds = None
		
		if self.force or not os.path.exists(output_rgb_fullname):		
			cmd = "gdaldem color-relief -q -alpha "+ output_fullname + " " + color_file + " " + output_rgb_fullname
			if self.verbose:
				print cmd
			os.system(cmd)
		
		# mbtiles
		if self.force or not os.path.exists(mbtiles_fname):		
			cmd = "./gdal2tiles.py -z " + tzoom + output_rgb_fullname  + " " + mbtiles_dir
			if self.verbose:
				print cmd
			os.system(cmd)

			cmd = "./mb-util " + mbtiles_dir  + " " + mbtiles_fname
			if self.verbose:
				print cmd
			os.system(cmd)
		
		# copy mbtiles to S3
		bucketName = region['bucket']
		cmd = "./aws-copy.py --bucket "+bucketName+ " --file " + mbtiles_fname
		if self.verbose:
			cmd += " --verbose "
			print cmd
		os.system(cmd)
	
		cmd = "rm -rf "+ mbtiles_dir
		os.system(cmd)
		
#
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)
	
	parser 		= argparse.ArgumentParser(description='MODIS Processing')
	apg_input 	= parser.add_argument_group('Input')
	apg_input.add_argument("-f", "--force", action='store_true', help="HydroSHEDS forces new water image to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	options = parser.parse_args()

	force		= options.force
	verbose		= options.verbose

	# Destination Directory
	dir			= config.data_dir
	
	app = GFMS( dir, force, verbose  )
	#app.get_latest_file()
	
	app.get_latest_highres_file()
	app.process_highres()