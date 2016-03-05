
import os
from osgeo import gdal
import numpy

verbose = 0
force 	= 0
		
def execute( cmd ):
	if verbose:
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
			cmd = str.format("potrace -i -z black -a 1.5 -t 3 -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", fileName+".geojson", fileName+".pgm", xres, xorg, ymax ); 
			
		execute(cmd)

		#cmd = str.format("node set_geojson_property.js --file {0} --prop frost={1}", fileName+".geojson", frost)
		#execute(cmd)
	
		out = ""
		if not verbose:
			out = "> /dev/null 2>&1"
			
		cmd = str.format("topojson -o {0} --simplify-proportion 0.5 -p {3}={1} -- {3}={2} {4}", fileName+".topojson", l, fileName+".geojson", attr, out );
		execute(cmd)
	
		# convert it back to json
		cmd = "topojson-geojson --precision 4 -o %s %s" % ( geojsonDir, fileName+".topojson" )
		execute(cmd)
	
		# rename file
		output_file = "%s_level_%d.geojson" % (attr, l)
		json_file	= "%s.json" % attr
		cmd = "mv %s %s" % (os.path.join(geojsonDir,json_file), os.path.join(geojsonDir, output_file))
		execute(cmd)
		