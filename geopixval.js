// Testing geopix

var geopix 		= require('geopix');
var tif			= geopix.GEOTIFFFile('../tmp/ojo-global/gfms/2015/286/flood_14km.20151013.tif')
var value		= tif.LatLng(24.75, 67.875)
console.log(value)
