import os, inspect, sys, math, urllib, glob, shutil
from osgeo import gdal

if 1:
	filename = '/Users/patricecappelaere/landslide/data/gpm_30mn/20160606/3B-HHR-E.MS.MRG.3IMERG.20160606-S130000-E132959.0780.V03E.30min.tif'
	try:
		ds 						= gdal.Open(filename)
	except Exception as e:
		print "IMERG File Read Error:", sys.exc_info()[0], e
		# if the read fails, we can try to delete the file
		#os.remove(filename)
		sys.exit(-1)
		
	geotransform			= ds.GetGeoTransform()
