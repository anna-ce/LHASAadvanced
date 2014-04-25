#!/usr/bin/env node

// converts a geojson file to osm

var path = require("path"),
    fs = require("fs"),
	util = require('util'),
	exec = require('child_process').exec,
	optimist = require("optimist"),
	eyes = require('eyes'),
	osm = require('osm-and-geojson')
	;
	
var version = '1.0.0';
	
var argv = optimist
	    .usage("Usage: \033[1mgeojson2osm\033[0m [options] [file …]\n\n"
		+ "Version: " + version + "\n\n"
		+ "Converts the specified input GeoJSON objects to OSM/PBF \n")
		.options("o", {
			alias: "out",
			describe: "outputfile name",
			default: "/dev/stdout",
		})
		.options("help", {
			describe: "display this helpful message",
			type: "boolean",
			default: false
		})
		.options("properties", {
			describe: "feature properties in json format",
			required: true
		})
		.demand(['properties'])
		.check(function(argv) {      
			if (argv.help) return;   
		})
		.argv;

if (argv.help) return optimist.showHelp();

var geojson 	= JSON.parse(fs.readFileSync(argv._[0]))
var properties	= JSON.parse(fs.readFileSync(argv.properties))

// We have to add OSM Tags here
var features	= geojson.features;
for( var f in features ) {
	features[f].properties = properties
}


var osm_xml			= osm.geojson2osm(geojson)
console.log("Writing osm to:", argv.o)
fs.writeFileSync(argv.o, osm_xml)
