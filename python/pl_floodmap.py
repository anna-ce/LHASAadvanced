#!/usr/bin/env python
#
# Created on 07/11/2014 Pat Cappelaere - Vightel Corporation
#
# Input: EO1 GeoTiff L1T
# Output: Top of Atmosphere Corrected Water map
#

# http://www.academia.edu/3107897/Shadow_Detection_and_Removal_from_Remote_Sensing_Images_Using_NDI_and_Morphological_Operators

import os, inspect, sys
import argparse

import numpy
import math, time
import scipy

from scipy import ndimage
from scipy import misc
from skimage.filter import sobel, threshold_isodata, threshold_otsu, rank
from skimage import color

from osgeo import gdal
from osgeo import osr
from osgeo import ogr
from which import *

import gdalnumeric
from PIL import Image
import colorsys

import config
import requests

force 		= 0
verbose		= 1

DATA_DIR		= "/Users/patricecappelaere/Development/ojo/ojo-bot/tmp"
PL_DIR			= DATA_DIR + "/planet-labs"
BASE_URL		= "https://api.planet.com/v0/scenes/ortho/"

def execute( cmd ):
	if verbose:
		print cmd
	os.system(cmd)
		
def download_full_image(scene):
	key 			= os.environ["PLANET_LABS_KEY"]
	url				= BASE_URL+scene+"/full"
	local_filename 	= os.path.join(PL_DIR, scene, scene+"_full.tif")
	if verbose:
		print "downloading full image from", url
	
	r = requests.get(url, stream=True, auth=(key, ''))
	
	#if 'content-disposition' in r.headers:
	#	local_filename = r.headers['content-disposition'] \
	#	.split("filename=")[-1].strip("'\"")
	#else:
	#	local_filename = '.'.join(url.split('/')[-2:])

	with open(local_filename, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024):
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)
				f.flush()

		return local_filename
	
#
# Apply Speckle filter
#
def speckle_filter(data, filter_name, ws):
	if verbose:
		print("filter it..")

	if filter_name == 'median':
		data = scipy.signal.medfilt2d(data, kernel_size=ws)
	elif filter_name == 'wiener':
		data = scipy.signal.wiener(data,mysize=(ws,ws),noise=None)
	return data
	

def rgb_to_hsv(rgb):
    # Translated from source of colorsys.rgb_to_hsv
    # r,g,b should be a numpy arrays with values between 0 and 255
    # rgb_to_hsv returns an array of floats between 0.0 and 1.0.
    rgb = rgb.astype('float')
    hsv = numpy.zeros_like(rgb)
    # in case an RGBA array was passed, just copy the A channel
    hsv[..., 3:] = rgb[..., 3:]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = numpy.max(rgb[..., :3], axis=-1)
    minc = numpy.min(rgb[..., :3], axis=-1)
    hsv[..., 2] = maxc
    mask = maxc != minc
    hsv[mask, 1] = (maxc - minc)[mask] / maxc[mask]
    rc = numpy.zeros_like(r)
    gc = numpy.zeros_like(g)
    bc = numpy.zeros_like(b)
    rc[mask] = (maxc - r)[mask] / (maxc - minc)[mask]
    gc[mask] = (maxc - g)[mask] / (maxc - minc)[mask]
    bc[mask] = (maxc - b)[mask] / (maxc - minc)[mask]
    hsv[..., 0] = numpy.select(
        [r == maxc, g == maxc], [bc - gc, 2.0 + rc - bc], default=4.0 + gc - rc)
    hsv[..., 0] = (hsv[..., 0] / 6.0) % 1.0
    return hsv
	
#https://github.com/jjberry/EchoTools/blob/master/EchoTools/Rgb2Hsv.py
def RGB2HSV(filename):
	i = Image.open(filename).convert('RGB')
	a = numpy.asarray(i, int)

	R, G, B = rgb.T
	
	print "red", numpy.amin(R), numpy.mean(R), numpy.amax(R)
	print "green", numpy.amin(G), numpy.mean(G), numpy.amax(G)
	print "blue", numpy.amin(B), numpy.mean(B), numpy.amax(B)
	
	m = numpy.min(rgb,2).T
	M = numpy.max(rgb,2).T
	 
	C = M-m #chroma
	Cmsk = C!=0
	 
	#Hue
	H = numpy.zeros(R.shape, int)
	mask = (M==R)&Cmsk
	H[mask] = numpy.mod(60*(G-B)/C, 360)[mask]
	mask = (M==G)&Cmsk
	H[mask] = (60*(B-R)/C + 120)[mask]
	mask = (M==B)&Cmsk
	H[mask] = (60*(R-G)/C + 240)[mask]
	H *= 180 #this controls the range of H
	H /= 360
	 
	#Value
	V = M

	#Saturation
	S = numpy.zeros(R.shape, int)
	S[Cmsk] = ((255*C)/V)[Cmsk]

	return H.T
	
#http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3274132/

def get_band_data(ds, num):
	band 	= ds.GetRasterBand(num)
	data	= band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize ).astype(float)
	return data

def linear_stretch(data, min_percentile=1.0, max_percentile=97.0):		
	if verbose:
		print 'linear_stretch', numpy.min(data), numpy.mean(data), numpy.max(data), min_percentile, max_percentile

	pmin, pmax = numpy.percentile(data[numpy.nonzero(data)], (min_percentile, max_percentile))
	if verbose:
		print "pmin:", pmin
		print "pmax:", pmax

	data[data>pmax]=pmax
	data[data<pmin]=pmin
		
	bdata = misc.bytescale(data)
	return bdata

def write_data(data, fileName, ds, type=gdal.GDT_Byte, nbands=1, ct=0):
	
	if verbose:
		print "write_data", fileName
	
	driver 		= gdal.GetDriverByName( "GTiff" )
	dst_ds 		= driver.Create( fileName, ds.RasterXSize, ds.RasterYSize, nbands, type, [ 'INTERLEAVE=PIXEL', 'COMPRESS=DEFLATE' ] )
	band 		= dst_ds.GetRasterBand(1)

	band.WriteArray(data, 0, 0)
	band.SetNoDataValue(0)

	if ct :
		if verbose:
			print "write ct"
		
		band.SetRasterColorTable(ct)
		
	if verbose:
		print "write geotransform and projection"
	
	dst_ds.SetGeoTransform( ds.GetGeoTransform() )
	dst_ds.SetProjection( ds.GetProjection() )
		
	if verbose:
		print "Written", fileName

	dst_ds 		= None
		
def threshold(data):
	thresh1	= threshold_otsu(data)
	thresh2 = thresh1*2
	print "ndi thresh", thresh1, thresh2
	data[data<thresh2] 	= 0
	data[data>=thresh2]	= 255
	return data

def reproject( epsg, in_file, out_file):
	# remove out_file if it already exists
	if os.path.isfile(out_file):
		os.remove(out_file)

	cmd = "gdalwarp -of GTiff -co COMPRESS=DEFLATE -t_srs "+ epsg +" " + in_file + " " + out_file
	execute(cmd)
		
# pl_floodmap.py --scene 8g3oO2
if __name__ == '__main__':
	parser 		= argparse.ArgumentParser(description='Generate EO-1 watermap')
	apg_input 	= parser.add_argument_group('Input')
	
	apg_input.add_argument("-f", "--force", 	action='store_true', help="Forces new product to be generated")
	apg_input.add_argument("-v", "--verbose", 	action='store_true', help="Verbose on/off")
	apg_input.add_argument("-s", "--scene", 	help="PlanetLabs Scene")
	
	options 	= parser.parse_args()
	force		= options.force
	verbose		= options.verbose
	
	outdir		= os.path.join(PL_DIR, options.scene)	
	scene	 	= options.scene

	infileName		= os.path.join(outdir, scene+"_full.tif")
	fileName		= os.path.join(outdir, scene+"_full_4326.tif")
	outfileName		= os.path.join(outdir, scene+"_watermap.tif")
	outfileName2	= os.path.join(outdir, scene+"_watermap2.tif")
	redfileName		= os.path.join(outdir, scene+"_red.tif")
	ratio1fileName	= os.path.join(outdir, scene+"_ratio1.tif")
	ratio2fileName	= os.path.join(outdir, scene+"_ratio2.tif")
	ratio3fileName	= os.path.join(outdir, scene+"_ratio3.tif")
	intfileName		= os.path.join(outdir, scene+"_int.tif")
	hfileName		= os.path.join(outdir, scene+"_hsv_h.tif")
	sfileName		= os.path.join(outdir, scene+"_hsv_s.tif")
	vfileName		= os.path.join(outdir, scene+"_hsv_v.tif")
	ndifileName		= os.path.join(outdir, scene+"_ndi.tif")
	topojsonfileName=os.path.join(outdir, "surface_water.topojson")
	
	if( not os.path.isfile(fileName)):
		# This is an issue, we need to download the full tif file first
		download_full_image(scene)
		
	if force or not os.path.isfile(fileName):
		reproject("EPSG:4326",infileName, fileName)
	
	ds = gdal.Open( fileName )
	if ds is None:
		print 'ERROR: file has no data:', fileName
		sys.exit(-1)

	geomatrix 	= ds.GetGeoTransform()
	rasterXSize = ds.RasterXSize
	rasterYSize = ds.RasterYSize

	xorg		= geomatrix[0]
	yorg  		= geomatrix[3]
	pres		= geomatrix[1]
	xmax		= xorg + geomatrix[1]* rasterXSize
	ymax		= yorg - geomatrix[1]* rasterYSize
	
	octagon_2 	=[
				[0, 1, 1, 1, 0],
				[1, 1, 1, 1, 1],
				[1, 1, 1, 1, 1],
				[1, 1, 1, 1, 1],
				[0, 1, 1, 1, 0]]
				
	print xorg, yorg, pres, xmax, ymax
	
	red						= get_band_data( ds, 1 ) 	
	green					= get_band_data( ds, 2 ) 	
	blue					= get_band_data( ds, 3 ) 	
	
	epsilon					= 0.0001
	norm_diff_ratio			= (red - blue) / (epsilon+blue+red)
	
	data1					= norm_diff_ratio
	data1					= speckle_filter(data1,'median', 11)
	data1					= linear_stretch(data1, max_percentile=50.0)	
	data1 					= ndimage.grey_opening(data1, size=(5,5), structure=octagon_2)
	thresh					= threshold_otsu(data1,nbins=7)
	print "otsu1", thresh
	data1[data1>=thresh] 	= 0
	data1[red==0] 			= 0
	#data1[data1>0]			= 255
	
	#thresh2					= threshold_otsu(data1,nbins=7)
	#print "otsu2", thresh2
	#data1[data1>thresh2] 	= 0
	
	write_data(data1, outfileName, ds)
	
	#norm_diff_ratio			= (red - green) / (epsilon+green+red)
	#data2					= linear_stretch(norm_diff_ratio)
	#write_data(data2, outfileName2, ds)

	#data3 	= red*1.0
	#thresh	= threshold_otsu(data3, nbins=7)
	#print "otsu", thresh
	#red[data3>thresh] = 0
	#data3 	= linear_stretch(data3, max_percentile=50.0)
	#rite_data(data3, redfileName, ds)
	#sys.exit(1)

	#data4 = green / (epsilon+red)
	#write_data(linear_stretch(data4), ratio1fileName, ds)
	
	#data5 = blue / (epsilon+red)
	#write_data(linear_stretch(data5), ratio2fileName, ds)

	#data6 = blue / (epsilon+green)
	#write_data(linear_stretch(data6), ratio3fileName, ds)
	
	#intensity = red/255.0 + green/255.0 + blue/255.0
	#write_data(linear_stretch(intensity), intfileName, ds)
	
	
	#rgb = numpy.array([red,green,blue]).T	
	#hsv = rgb_to_hsv(rgb)
	#h,s,v = hsv.T
	
	#print "h", numpy.amin(h), numpy.mean(h), numpy.amax(h)
	#print "s", numpy.amin(s), numpy.mean(s), numpy.amax(s)
	#print "v", numpy.amin(v), numpy.mean(v), numpy.amax(v)
	
	#write_data(misc.bytescale(h), hfileName, ds)
	#write_data(misc.bytescale(s), sfileName, ds)
	#write_data(misc.bytescale(v), vfileName, ds)
	
	#ndi 	= (s-v)/(s+v+epsilon)
	#data	= speckle_filter(ndi,'median', 11)
	#data	= linear_stretch(ndi)
	
	#
	# Morphing to smooth and filter the data
	#

	#data 	= ndimage.grey_opening(data, size=(5,5), structure=octagon_2)
	#data[red==0] 		= 0
	#data 	= threshold(data)
	#write_data(data, ndifileName, ds)	
	#sys.exit(1)
	
	file = outfileName + ".pgm"
	
	cmd = "gdal_translate  -q -scale 0 1 0 65535 " + ndifileName + " -b 1 -of PNM -ot Byte "+file
	execute( cmd )
	execute("rm -f "+file+".aux.xml")

	# -i  		invert before processing
	# -t 2  	suppress speckles of up to this many pixels. 
	# -a 1.5  	set the corner threshold parameter
	# -z black  specify how to resolve ambiguities in path decomposition. Must be one of black, white, right, left, minority, majority, or random. Default is minority
	# -x 		scaling factor
	# -L		left margin
	# -B		bottom margin

	if force or not os.path.exists(file+".geojson"):
		cmd = str.format("potrace -z black -a 1.5 -t 10 -i -b geojson -o {0} {1} -x {2} -L {3} -B {4} ", file+".geojson", file, pres, xorg, ymax ); 
		execute(cmd)

	if force or not os.path.exists(topojsonfileName+".gz"):
		cmd = str.format("topojson -o {0} --simplify-proportion 0.75 -- surface_water={1}", topojsonfileName, file+".geojson"); 
		execute(cmd)

		# gzip it
		cmd = str.format("gzip {0} ", topojsonfileName ); 
		execute(cmd)

	dst_ds 		= None
	ds			= None
