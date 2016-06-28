// Pat Cappelaere, Vightel Corproation
// Jun 18, 2016
//
// Application to subset global geojson into regional topojson files
//
var fs 							= require('fs');
var path						= require('path');
var turf						= require('turf');

var turf_bbox_clip				= require('./lib/turf-bbox-clip');
var exec 						= require('child_process').exec;

var script						= process.argv[1]
var regionName					= process.argv[2]
var geojson_file				= process.argv[3]

var dir							= path.dirname(geojson_file)
var baseName					= path.basename(geojson_file)

var topoBaseName				= baseName.replace('geojson', "topojson")

var regional_geojson_filename	= path.join(dir, "..", regionName, baseName)
var regional_topojson_filename	= path.join(dir, "..", regionName, topoBaseName)

// console.log("Subsetting", regionName, geojson_file)

var regions			= JSON.parse(fs.readFileSync('../imerg_regions.yaml', 'utf-8'))
var geojson			= JSON.parse(fs.readFileSync(geojson_file, 'utf-8'))

function generate() {
	try {
		var region 	= regions.regions[regionName]
		var bbox	= region.bbox
	
		// Make a polygon
		var poly1 	= turf.bboxPolygon( bbox )
	
		var features = [];	
		for (var f in geojson.features ) {
			try {
				var poly2 = geojson.features[f]
				var result = turf_bbox_clip(poly2, bbox )
				if(result.geometry.coordinates.length) {
					features.push(result)
				}
			} catch(e) {
				console.log("turf exception", e)
				console.log("dies in", f, JSON.stringify(geojson.features[f]))
			
				break;
			}
		}
		
		var regional_geojson = {
			type: "FeatureCollection",
			features: features
		}	
				
		fs.writeFileSync(regional_geojson_filename, JSON.stringify(regional_geojson), "utf-8")
		// console.log("written", regional_geojson_filename)

		var cmd = "topojson -o " + regional_topojson_filename + " -p -- " + regional_geojson_filename 
		cmd += "; gzip "+regional_topojson_filename
		
		var child = exec(cmd, function (error, stdout, stderr) {
		    //console.log('stdout: ' + stdout);
		    //console.log('stderr: ' + stderr);
			
			if (error !== null) {
				console.log('exec error: ' + error);
			} else {
				//console.log("written", regional_topojson_filename)
			}
		})
	} catch(e) {
		console.log("Error Exception", e)
	}
}

generate()