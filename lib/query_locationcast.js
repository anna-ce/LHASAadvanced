var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	sprintf 	= require("sprintf-js").sprintf,
	_			= require('underscore'),
	Hawk		= require('hawk'),
	filesize 	= require('filesize')
	;
	
	function padDoy( doy ) {
		if( doy < 10 ) {
			doy = "00"+doy
		} else if( doy < 100 ) {
			doy = "0"+doy
		}
		return doy
	}

	function InBBOX( lat, lon, bbox) {
		if( (lat > bbox[1]) && (lat< bbox[3]) && (lon > bbox[0]) && (lon < bbox[2]) ) return true;
		return false
	}

	function findRegion(lat, lon) {
		if( InBBOX(lat, lon, app.config.regions.d02.bbox)) return app.config.regions.d02
		if( InBBOX(lat, lon, app.config.regions.d03.bbox)) return app.config.regions.d03
		return undefined
	}

	function regionId( region ) {
		var dx = "d03"
		if( region === app.config.regions.d02 ) dx = "d02"
		return dx
	}
	
	function LocationcastProductId(region, ymd, lat, lon) {
		return "location_cast_"+regionId(region)+"_"+ymd+"_"+lat+"_"+lon
	}
	
	function QueryLocationCast(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
		if( query != 'location_cast' ) {
			logger.info("QueryLocationCast unsupported query", query)
			return cb(null, null)
		}

		var ymd = moment().format("YYYYMMDD")
		
		// find region of interest
		var region = findRegion(lat, lon)
		if( region === undefined ) {
			console.log("Undefined region for ", lat, lon)
			return cb(null, null)
		}
				
		var url = "http://api.tiles.mapbox.com/v4/"+region.map_id+"/"
		url += "pin-m-circle+ff0000("+lon+","+lat+")"
		url += "/" + lon +"," + lat+",10/256x256.png32?access_token="+app.config.mapboxToken
		
		console.log("QueryLocationcast", limit, region.name, url)
		
		var entry = {
			"@id": 	LocationcastProductId(region, ymd, lat, lon),
			"@type": "geoss:locationcast",
			"image": [
				{
					"url": url,
					"mediaType": "image/png",
					"rel": "browse"
				}
			],
			"properties": {
				'landslide_nowcast': 			0,
				'landslide_forecast': 			0,
				'flood_nowcast': 				0,
				'flood_forecast': 				0,
				'precipitation_nowcast': 		0,
				'precipitation_forecast': 		0,
				'soil_moisture_nowcast': 		0,
				'soil_moisture_forecast': 		0
			}
		}
		var entries = [entry]
		var json = {
			replies: {
				items: entries
			}
		}
		cb(null, json)	
	}
	module.exports.QueryLocationCast 	= QueryLocationCast;
	