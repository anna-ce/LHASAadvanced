var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	sprintf 	= require("sprintf-js").sprintf,
	_			= require('underscore'),
	Hawk		= require('hawk'),
	filesize 	= require('filesize'),
	assert	 	= require("assert")
	;

// https://www.planet.com/docs/

function checkPlanetLabs( req, query, user, bbox, credentials, entries, params, callback ) {
	var url 	= "https://api.planet.com/v0/scenes/ortho/";
	var key	 	= process.env.PLANET_LABS_KEY;
	var host 	= req.protocol + "://"+ req.get('Host')
		
	assert(key)
		
	function Bewit(url) {
		if( credentials ) {
			var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
			url += "?bewit="+bewit
		}
		return url;
	}
	
	var sf_nw 	= [bbox[0], bbox[3]]
	var sf_se 	= [bbox[2], bbox[1]]
		
	var sf_ne 	= [sf_se[0], sf_nw[1]];
	var sf_sw 	= [sf_nw[0], sf_se[1]];
	var bounds 	= [sf_nw, sf_ne, sf_se, sf_sw, sf_nw];

	var bounds_joined = [];

	for (var i=0; i<bounds.length; i++) {
	    bounds_joined.push(bounds[i].join(' '));
	}

	var intersects = "POLYGON((" + bounds_joined.join(', ') + "))";

	params["intersects"] 				= intersects
	params["cloud_cover.estimated.lte"] = 0.1

	console.log(url)
	console.log(params)
	
	var request = require('request');
	var auth = "Basic " + new Buffer(key + ":").toString("base64");

	request({
	    url: url,
	    qs: params,
	    method: "GET",
	    headers: {
	        "Authorization": auth
	    },
	}, function (error, response, body) {
		console.log("PlanetLabs error", error)
	    if (!error) {
			//console.log(body)
	        var data = JSON.parse(body);
	        // do something with data.features here
			console.log("Num Features Acquired from PlanetLabs:", data.features.length)
			_.each(data.features, function(feature) {
				//console.log("Scene", feature.id, "cloud cover", feature.properties.cloud_cover.estimated)
				//console.log(feature)
				
				var base_url = host+"/products/planetlabs/"+feature.id
				
				var properties = {
					"date": {
						"@label": "acquired",
						"@value": feature.properties.acquired
					},
					"source": {
						"@label": "source",
						"@value": "Planet-Labs Dove"
					},
					"resolution": {
						"@label": "resolution",
						"@value": "3m"
					},
					"cloud_cover": {
						"@label": "cloud_cover",
						"@value": feature.properties.cloud_cover.estimated
					},
					"file_size": {
						"@label": "file_size",
						"@value": feature.properties.file_size
					},
					"snr": {
						"@label": "snr",
						"@value": feature.properties.image_statistics.snr
					},
					"sat_altitude": {
						"@label": "sat_altitude",
						"@value": feature.properties.sat.alt
					},
					"sat_latitude": {
						"@label": "sat_latitude",
						"@value": feature.properties.sat.lat
					},
					"sat_longitude": {
						"@label": "sat_longitude",
						"@value": feature.properties.sat.lng
					},
					"sun_altitude": {
						"@label": "sun_altitude",
						"@value": feature.properties.sun.altitude
					},
					"sun_azimuth": {
						"@label": "sun_azimuth",
						"@value": feature.properties.sun.azimuth
					},
					"local_time_of_day": {
						"@label": "local_time_of_day",
						"@value": feature.properties.sun.local_time_of_day
					}
				};
				
				var downloads = undefined;
				
				if( query == 'rgb_composite' ) {
					var tiff_file_url = base_url + "/full"
					downloads = { 
						"@type": 			"ojo:download",
						"displayName": 		req.gettext("actions.download"),
						"using": [{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			Bewit(tiff_file_url),
							"mediaType": 	"image/tiff",
							"displayName": 	req.gettext("formats.geotiff")
						}]
					}
				} else {
					var topojson_url  = host+"/products/planetlabs/"+feature.id+"/surface_water.topojson"	
					var topojson_file = app.get("tmp_dir") + "/tmp/planet-labs/"+feature.id+"/surface_water.topojson.gz"
					if( fs.existsSync(topojson_file)) {
						downloads = { 
							"@type": 			"ojo:download",
							"displayName": 		req.gettext("actions.download"),
							"using": [{
									"@type": 		"as:HttpRequest",
									"method": 		"GET",
									"url": 			Bewit(topojson_url+".gz"),
									"mediaType": 	"application/gzip",
									//"size": 		app.locals.GetFileSize(topojson_file, req.gettext),
									"displayName": 	req.gettext("formats.topojsongz")
								},
								{
									"@type": 		"as:HttpRequest",
									"method": 		"GET",
									"url": 			Bewit(topojson_url),
									"mediaType": 	"application/json",
									//"size": 		app.locals.GetFileSize(topojson_file, req.gettext),
									"displayName": 	req.gettext("formats.topojson")
								}
							]
						}
					} else {
						console.log(topojson_file, "does not exist")
					}
				}
				
				var actions = [
					{ 
						"@type": 			"ojo:browse",
						"displayName": 		req.gettext("actions.browse"),
						"using": [{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			base_url+"?q="+query,
							"mediaType": 	"html",
						}]
					}	
				]
				
				if( downloads ) actions.push(downloads)
				
				if( (query == 'surface_water') && !fs.existsSync(topojson_file)) {
					var minutes = 5
					var process = {
						"@type": 		"ojo:process",
						"displayName": 	req.gettext("actions.process"),
						"using": [{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			Bewit(host+"/products/planetlabs/"+feature.id+"/process"),
							"displayName": 	req.gettext("products.surface_water"),
							"duration": 	util.format(req.gettext("duration.minutes").replace('{minutes}', 'd'),minutes)
						}]
					}
					actions.push(process)
				}
				
				var entry = {
					"@id": 	feature.id,
					"@type": "geoss:rgb_composite",
					"image": [
						{
							"url": base_url+"/thn",
							"mediaType": "image/png",
							"rel": "browse"
						}
					],
					"properties": properties,
					"geometry": feature.geometry,
					"action": actions
				}
				
				entries.push(entry)
			})
	    }
		callback(error)
	});
}

function QueryPlanetLabs(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
	var ymds = []
	
	//console.log("QueryPlanetLabs bbox", bbox, "lat/lon", lat, lon)
	
	entries		= []
	if( (query != "rgb_composite") && (query != "surface_water")) {
		var json = {
			replies: {
				items: entries
			}
		}
		cb(null, json)	
		return
	}
		
	var options = {
	    'acquired.gte': startTime.toISOString(),
	    'acquired.lte': endTime.toISOString(),
		'count':  		limit,
		'order_by': 	'acquired desc'
	};
	
	checkPlanetLabs( req, query, user, bbox, credentials, entries, options, function(err) {
		console.log("checkPlanetLabs Done", err, entries.length)
		var json = {
			replies: {
				items: entries
			}
		}
		cb(null, json)	
	})
}

module.exports.QueryPlanetLabs	= QueryPlanetLabs;
