#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
import numpy, sys, os, inspect, urllib
import argparse

from osgeo import osr, gdal
from ftplib import FTP
from datetime import date, timedelta

# Site configuration
import config

oneday		= timedelta(days=1)

today 		= config.today
year		= config.year
month		= config.month
day			= config.day

print today
#year 		= 2013
#month		= 10
#day		= 1
#today		= date(year, month, day)

jd			= today.timetuple().tm_yday

class MODIS:
	def __init__( self, inpath, year, day, product, region, force, verbose ):
		self.inpath					= inpath
		self.year				 	= year		
		self.day				 	= day
		self.product				= product
		self.force					= force
		self.verbose				= verbose
		self.region					= region
		
		# Mosaic File Name
		mosaic 			= str.format("MODIS_{0}{1}_mosaic_{2}D{2}OT.vrt", year, day, product)
		swp				= str.format("MODIS_{0}{1}_{2}D{2}OT.tif", year, day, product)
		pnm 			= str.format("MODIS_{0}{1}_{2}D{2}OT.pnm", year, day, product)
		pgm 			= str.format("MODIS_{0}{1}_{2}D{2}OT.pgm", year, day, product)
		bmp 			= str.format("MODIS_{0}{1}_{2}D{2}OT.bmp", year, day, product)
		geojson 		= str.format("MODIS_{0}{1}_{2}D{2}OT.geojson", year, day, product)
		topojson 		= str.format("MODIS_{0}{1}_{2}D{2}OT.topojson", year, day, product)
		tgz		 		= str.format("MODIS_{0}{1}_{2}D{2}OT.topojson.tgz", year, day, product)
		svg		 		= str.format("MODIS_{0}{1}_{2}D{2}OT.svg", year, day, product)
		#png		 		= str.format("MODIS_{0}{1}_{2}D{2}OT.png", year, day, product)
			
		self.infile 	= os.path.join( inpath, mosaic )
		self.swp		= os.path.join( inpath, swp )
		self.pnm		= os.path.join( inpath, pnm )
		self.pgm		= os.path.join( inpath, pgm )
		self.geojson	= os.path.join( inpath, geojson )
		self.topojson	= os.path.join( inpath, topojson )
		self.tgz		= os.path.join( inpath, tgz )
		#self.png		= os.path.join( inpath, year, day, png )
		#self.bmp		= os.path.join( inpath, year, day, bmp )
		self.bmp		= os.path.join( inpath, bmp )
		
		if self.verbose:
			print self.infile


	def get_daily_modis_tiles( self ):	
		print self.region['modis_tiles']
		for tile in self.region['modis_tiles']:
			self.get_daily_modis_tile(tile)
	
		self.build_daily_mosaic()

	def build_daily_mosaic(self):
		filestar 		= os.path.join(self.inpath, "*_MWP_%s%s_*_%dD%dOT.tif" % (self.year, self.day, self.product, self.product))
		bbox			= self.region['bbox']
		if not os.path.exists( self.infile ):
			#cmd = "gdal_merge.py -o "+ 	self.infile + " " + filestar
			cmd = "gdalbuildvrt -q -addalpha -overwrite -te %f %f %f %f %s %s" % ( bbox[0], bbox[1], bbox[2], bbox[3], self.infile, filestar)
			if self.verbose:
				print cmd
			err = os.system(cmd)
	
	def get_daily_modis_tile( self, tile ):	
		baseName		= "MWP_%s%s_%s_%dD%dOT.tif" % (self.year, self.day, tile, self.product, self.product )
		baseUrl			= "http://oas.gsfc.nasa.gov/Products/%s/%s" % (tile, baseName)
		basefilename 	= os.path.join(self.inpath, "%s_%s" % (tile, baseName))

		if force or not os.path.exists(basefilename):
			if self.verbose:
				print "retrieving ", baseUrl, '->', basefilename
			local_filename, headers = urllib.urlretrieve(baseUrl, basefilename)
			print "retrieved ", headers
			print "Content-Length:", headers['Content-Length']
			if headers['Content-Length'] == '246':
				# File did not exist
				raise Exception("WARNING: File:"+baseUrl+ " is not available!!")
		else:
			if self.verbose:
				print "found ", basefilename
			
	
	def open_geotiff(self):
		ds = gdal.Open( self.infile )
		if ds is None:
			print('ERROR: could not open MODIF Tif file:', self.insfile)
			sys.exit(-1)

		self.ds 			= ds	
		self.RasterXSize 	= ds.RasterXSize
		self.RasterYSize 	= ds.RasterYSize
		self.RasterCount 	= ds.RasterCount

		if self.verbose:
			print 'Size is ',ds.RasterXSize,'x',ds.RasterYSize, 'x',ds.RasterCount

		projection   = ds.GetProjection()
		if self.verbose:
			print 'Projection is ',projection

		geotransform = ds.GetGeoTransform()
		if not geotransform is None:
			if self.verbose:
				print 'Origin = (',geotransform[0], ',',geotransform[3],')'
				print 'Pixel Size = (',geotransform[1], ',',geotransform[5],')'

		self.xorg	= geotransform[0]
		self.yorg  	= geotransform[3]
		self.res	= geotransform[1]		
		self.xmax	= geotransform[0] + ds.RasterXSize * geotransform[1]
		self.ymax	= geotransform[3] + ds.RasterYSize * geotransform[5]

		if self.verbose:
			print self.xorg, self.xmax, self.yorg, self.ymax
	
	def process(self):
		# Surface Water
		band = self.ds.GetRasterBand(1)
		data = band.ReadAsArray(0, 0, self.ds.RasterXSize, self.ds.RasterYSize )
		data = (data >= 3)

		# Step 1
		# extract surface water from MWP product
		#
		driver 		= gdal.GetDriverByName( "GTIFF" )
		dst_ds 		= driver.Create( self.swp, self.RasterXSize, self.RasterYSize, 1, gdal.GDT_Byte, [ 'INTERLEAVE=PIXEL', 'COMPRESS=DEFLATE' ] )

		ct = gdal.ColorTable()
		for i in range(256):
			ct.SetColorEntry( i, (255, 255, 255, 255) )

		ct.SetColorEntry( 0, (0, 0, 0, 255) )
		ct.SetColorEntry( 1, (255, 255, 255, 255) )
		ct.SetColorEntry( 2, (255, 255, 255, 255) )
		ct.SetColorEntry( 3, (255, 255, 255, 255) )

		band = dst_ds.GetRasterBand(1)
		band.SetRasterColorTable(ct)
		band.WriteArray(data, 0, 0)
		band.SetNoDataValue(0)

		#dst_ds.SetGeoTransform( geotransform )
		#dst_ds.SetProjection( projection )

		dst_ds 		= None
		self.ds 	= None

		self.convert_to_pgm()
		self.convert_to_geojson(self.res, self.xorg, self.yorg)
		self.convert_to_topojson()

		os.system("rm -f "+ self.pnm + ".aux.xml")		

	def convert_to_pgm(self):
		# Step 2
		# output to .pgm using PNM driver
		# we may be able to skip that step and do it in step 1
		#cmd = "gdal_translate  -q " + self.swp + " -b 1 -of PNM -ot Byte "+self.pgm
		#print( cmd )
		#os.system(cmd)

		#cmd = "convert " + self.swp + " "+self.pgm
		#if self.verbose:
		#	print( cmd )
		#os.system(cmd)

		# subset it, convert red band (band 1) and output to .pgm using PNM driver
		cmd = "gdal_translate -b 1 -of BMP -ot Byte %s %s" % (self.swp, self.bmp)
		os.system(cmd)
		if verbose:
			print( cmd )
		os.system("rm -f "+self.bmp+".aux.xml")


	def convert_to_geojson(self, res, xorg, yorg):
		# Step 3
		# create geojson
		cmd = str.format("potrace -z black -a 1.5 -t 1 -i -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", self.geojson, self.bmp, self.res, self.xorg, self.ymax ); 
		if self.verbose:
			print(cmd)
		os.system(cmd)

	def convert_to_topojson(self):
		# Step 4
		# create topojson
		cmd = str.format("topojson --bbox --simplify-proportion 0.5 {0} -o {1} ", self.geojson, self.topojson ); 
		if self.verbose:
			print(cmd)
		os.system(cmd)

		# Step 4
		# compress topojson without all the directories
		cmd = str.format("tar -czf {0} -C {1}  {2} ", self.tgz, self.inpath, os.path.basename(self.topojson)); 
		if self.verbose:
			print(cmd)
		os.system(cmd)

	# Delete all product
	def clear(self):
	 	all = os.path.join( self.inpath, "MODIS_*_%dD*" % self.product )
		cmd = str.format("rm -f {0}", all );
		if self.verbose:
			print(cmd)
		os.system(cmd)

	def copy_to_s3(self):
		bucketName 	= self.region['bucket']
		
		cmd = "./aws-copy.py --bucket "+bucketName+ " --file " + self.tgz
		if self.verbose:
			cmd += " --verbose "
			print cmd
		os.system(cmd)
			
		
def process_modis_region( dx , force, verbose ):
	# make sure it exists
	region		= config.regions[dx]
	
	print "Processing Modis for Region:", dx, region['name']	
	
	# Destination Directory
	dir			= os.path.join(config.data_dir, "modis", dx)
	if not os.path.exists(dir):
		os.mkdir(dir)
	
	# two-day product
	product 	= 2
	
	app = MODIS(dir, str(year), "%02d"%jd, product, region, force, verbose)
	app.get_daily_modis_tiles()
	app.open_geotiff()
	#app.clear()
	app.process()
	#app.copy_to_s3()
	
#
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)
	
	# Make sure we have proper environment variables
	try:
		aws_key 	= os.environ['AWS_ACCESSKEYID']
		aws_secret 	= os.environ['AWS_SECRETACCESSKEY']

	except:
		print "Unavailable AWS keys", sys.exc_info()[0]
		sys.exit(-1)
		
	parser 		= argparse.ArgumentParser(description='MODIS Processing')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", action='store_true', help="forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", action='store_true', help="Verbose Flag")
	options = parser.parse_args()

	force		= options.force
	verbose		= options.verbose

	process_modis_region("d02", force, verbose)
	process_modis_region("d03", force, verbose)
	

