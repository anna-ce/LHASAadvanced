#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#	gdal, numpy pytrmm...
#
# Access and Process NCEP Soil Moisture
#

import numpy, sys, os, inspect
from osgeo import osr, gdal
from ftplib import FTP
from datetime import date
import pygrib

# Site configuration
import config

today 		= date.today()
year		= today.year
month		= today.month
day			= today.day

year 		= 2013
month		= 10
day			= 1

ftp_site 	= "ftpprd.ncep.noaa.gov"
gdasdir		= "gdas.%d%02d%02d" % (year, month, day)
path	 	= "pub/data/nccf/com/gfs/prod/" + gdasdir

#
# Process NCEP GRIB2 data to get soil moisture
#
def process_ncep_file( filename ):
	print "processing: "+filename
	grbs 	= pygrib.open(filename)
	
	#for grb in grbs:
	#	print grb
	
	sma	 	= grbs.select(name='Soil moisture content')
	print sma
	
	sm		= sma[0]
	data 	= sm['values']

	smastr 	= "%s"%sm
	arr 	= smastr.split(':')
	id 		= arr[0]
	
	print "min/mean/max/stdev:", data.min(),data.mean(),data.max(),data.std()
	
	nrows 	= data.shape[0]
	ncols 	= data.shape[1]	 

	y 		= 89.84
	x 		= 0		
	xres 	= 0.204432
	yres	= 0.204182
	
	# flip the array because it starts at -89.84
	flipped_data 		= numpy.flipud(data)
	
	# Set file vars
	delete_files 		= os.path.join(config.data_dir,"gdas","ncep_out_*")
	output_file 		= os.path.join(config.data_dir,"gdas","ncep_out_4326.tif")
	rgb_output_file 	= os.path.join(config.data_dir,"gdas","ncep_out_4326_rgb.tif")
	subset_file 		= os.path.join(config.data_dir,"gdas","ncep_out_subset_4326.tif")
	subset_rgb_file 	= os.path.join(config.data_dir,"gdas","ncep_out_subset_4326_rgb.tif")
	color_file 			= os.path.join("cluts","ncep_colors.txt")
	resampled_file 		= os.path.join(config.data_dir,"gdas","ncep_out_subset_4326_1km.tif")
	resampled_rgb_file 	= os.path.join(config.data_dir,"gdas","ncep_out_subset_4326_1km_rgb.tif")

	cmd = "rm " + delete_files
	print cmd
	os.system(cmd)
	
	# Create gtif
	driver = gdal.GetDriverByName("GTiff")
	dst_ds = driver.Create(output_file, ncols, nrows, 1, gdal.GDT_Float32 )

	# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
	dst_ds.SetGeoTransform( [ x, xres, 0, y, 0, -yres ] )
  
	# set the reference info 
	srs = osr.SpatialReference()
	srs.SetWellKnownGeogCS("WGS84")
	dst_ds.SetProjection( srs.ExportToWkt() )

	# write the band
	band = dst_ds.GetRasterBand(1)
	band.SetNoDataValue(9999)	# fill value
	band.WriteArray(flipped_data)
	dst_ds = None
	
	# color it using colormap
	#cmd = "gdaldem color-relief -q -alpha " + output_file + " " + color_file + " " + rgb_output_file
	#print cmd
	#os.system(cmd)

	# subset it to our BBOX
	lonlats	= "" + str(config.bbox[0]) + " " + str(config.bbox[1]) + " " + str(config.bbox[2]) + " " + str(config.bbox[3])
	cmd 	= "gdal_translate -q -projwin " + lonlats +" " + output_file + " " + subset_file
	print cmd
	os.system(cmd)

	# color it using colormap
	#cmd = "gdaldem color-relief -q -alpha " + subset_file + " " + color_file + " " + subset_rgb_file
	#print cmd
	#os.system(cmd)

	# resample it at 1km
	cmd = "gdalwarp -q -tr 0.008999 0.008999 -r near " + subset_file + " " + resampled_file
	print cmd
	os.system(cmd)

	# color it using colormap
	cmd = "gdaldem color-relief -q -alpha " + resampled_file + " " + color_file + " " + resampled_rgb_file
	print cmd
	os.system(cmd)
	
#import pygrib
#grbs = pygrib.open('gdas1.t06z.sfluxgrbf00.grib2')
#for grb in grbs: print grb
#grb = grbs[96]
#data = grb['values']
#'shape/min/max data %s %6.2f %6.2f'%(str(data.shape),data.min(),data.max())
#'shape/min/max data (880, 1760) 192.65 2000.01'
#lats, lons = grb.latlons() 
#str('min/max of %d lats on %s grid %4.2f %4.2f' % (grb['Nj'], grb['typeOfGrid'],lats.min(),lats.max()))
#'min/max of 880 lats on regular_gg grid -89.84 89.84'
#str('min/max of %d lons on %s grid %4.2f %4.2f' % (grb['Ni'], grb['typeOfGrid'],lons.min(),lons.max()))
#'min/max of 1760 lons on regular_gg grid 0.00 359.80'
#bbox latitude: -89.84 to 89.84 res: 0.204432
#bbox longitude: 0..359.80 res: 0.204432


#
# Get latest NCEP file from FTP site
#
def get_latest_ncep_file():
	
	print("Checking ftp://"+ ftp_site + " for latest file...")
	ftp = FTP(ftp_site)
	
	try:
		ftp.login()               					# user anonymous, passwd anonymous@
		print("cwd to "+ path)
	
		ftp.cwd( path )
		filenames = []
	
		def getsfluxgrbf(name):
			#print name
			if name.find("sfluxgrbf") > 0 and name.find("idx") < 0:
				filenames.append(name)
			
		ftp.retrlines('NLST', getsfluxgrbf )

		downwload = filenames[len(filenames)-1]
		print "latest is: ", downwload	

		local_filename = os.path.join(config.data_dir, "gdas", gdasdir+"."+downwload)
		if os.path.exists(local_filename):
			return local_filename
		else:
			print "Downloading ", local_filename
			file = open(local_filename, 'wb')
			ftp.retrbinary("RETR " + downwload, file.write)
			ftp.close()
			return local_filename
	except:
		print "FTP Error",sys.exc_info()[0]
		ftp.close()
		sys.exit(1)
	
#
# ======================================================================
#
if __name__ == '__main__':
	version_num = int(gdal.VersionInfo('VERSION_NUM'))
	if version_num < 1800: # because of GetGeoTransform(can_return_null)
		print('ERROR: Python bindings of GDAL 1.8.0 or later required')
		sys.exit(1)

	latest_file = get_latest_ncep_file()
	process_ncep_file( latest_file)
	
	#process_ncep_file( os.path.join(config.data_dir,"gdas.20131003.gdas1.t00z.sfluxgrbf00.grib2"))
	
