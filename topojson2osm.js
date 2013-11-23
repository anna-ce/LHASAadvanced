#!/usr/local/n/versions/0.10.8/bin/node

// converts a topojson file to osm

var path = require("path"),
    fs = require("fs"),
	util = require('util'),
	exec = require('child_process').exec,
	topojson = require('topojson'),
	optimist = require("optimist"),
	eyes = require('eyes'),
	osm = require('osm-and-geojson')
	;
	
var version = '1.0.0';
	
var argv = optimist
	    .usage("Usage: \033[1mtopojson2osm\033[0m [options] [file …]\n\n"
		+ "Version: " + version + "\n\n"
		+ "Converts the specified input TopoJSON objects to PBF \n")
		.options("o", {
			alias: "out",
			describe: "output PBF file name",
			default: "/dev/stdout",
		})
		.options("help", {
			describe: "display this helpful message",
			type: "boolean",
			default: false
		})
		.check(function(argv) {      
			if (argv.help) return;   
		})
		.argv;

if (argv.help) return optimist.showHelp();

// topojson2osm.js /Volumes/MacBay3/landslide/data/modis/d03/MODIS_2013299_2D2OT.topojson

var topojsonFile = argv._[0];
var topology = JSON.parse(fs.readFileSync(topojsonFile));
if( topology.type != 'Topology') {
	console.log("Not a topojson file")
	process.exit(-1);
}

if( topology.bbox == undefined ) {
	console.log("Missing topology bbox")
	process.exit(-1)
}

eyes.inspect(topology.bbox, "topology.bbox");

//eyes.inspect(topology, "topology")
//var geojson = topojson.feature(topology, "MODIS_2013299_2D2OT");

var keys 	= Object.keys(topology.objects);
var k 		= keys[0];

console.log("convert to geojson...")
// and preserve bbox
var geojson 	= topojson.feature(topology, topology.objects[k]);
geojson.bbox	= topology.bbox
if( geojson.bbox == undefined ) {
	console.log("Missing geojson bbox")
	process.exit(-1)
}

// save it to the file
var dirname 			= path.dirname(topojsonFile)
var basename 			= path.basename(topojsonFile, ".topojson")
var osmFile 			= path.join(dirname, basename + "_3857.osm")
var geojson_4326_File 	= path.join(dirname, basename + "_4326.geojson")
var geojson_3857_File 	= path.join(dirname, basename + "_3857.geojson")
var pbfFile 			= path.join(dirname, basename + "_3857.pbf")

fs.writeFileSync(geojson_4326_File, JSON.stringify(geojson))

// reproject to 3857
cmd = "rm " + geojson_3857_File + ";\n ogr2ogr -s_srs 'epsg:4326' -t_srs 'epsg:3857' -f 'GeoJSON' "+geojson_3857_File+" "+geojson_4326_File
console.log(cmd)
exec(cmd, function(err, stdout, stderr) {
	console.log(err, stdout)
	if( !err ) {
		console.log("convert to osm...",osmFile)
		var geojson_3857 	= JSON.parse(fs.readFileSync(geojson_3857_File));
		var osm_xml			= osm.geojson2osm(geojson_3857)
		fs.writeFileSync(osmFile, osm_xml)

		// now we need to convert this to PBF

		//cmd = "osmconvert "+osmFile+" --out-pbf > " + pbfFile;
		//console.log(cmd)
		//exec(cmd, function(err, stdout, stderr) {
			console.log("Done.", err)
			//})
	}
})

