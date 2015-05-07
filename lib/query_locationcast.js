var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	sprintf 	= require("sprintf-js").sprintf,
	_			= require('underscore'),
	Hawk		= require('hawk'),
	//gdal		= require('gdal'),
	geopix		= require('geopix'),
	mkdirp		= require('mkdirp'),
	filesize 	= require('filesize'),
	debug		= require('debug')('locationcast'),
	assert		= require('assert'),
	Forecast 	= require('forecast.io');
	
	assert(process.env.FORECAST_API_KEY, "undefined FORECAST_API_KEY env");
	
	var options = {
	  APIKey: process.env.FORECAST_API_KEY,
	  timeout: 1000
	}
	var forecast = new Forecast(options);
	
	
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
		if( InBBOX(lat, lon, app.config.regions.d07.bbox)) return app.config.regions.d07
		return undefined
	}

	function regionId( region ) {
		var dx = "d03"
		if( region == app.config.regions.d02 ) {
			dx = "d02"
		} else if( region == app.config.regions.d07 ) {
			dx = "d07"
		}
		return dx
	}
	
	function LocationcastProductId(region, ymd, lat, lon) {
		return "location_cast_"+regionId(region)+"_"+ymd+"_me"
	}
	
	function getGeopixValue(fileName, lat, lng) {
		debug("getGeopixValue", fileName, lat, lng)
		try {
			var tif				= geopix.GEOTIFFFile(fileName)
			return tif.LatLng(lat, lng)
		} catch(e) {
			logger.error("getGeopixValue Exception", e)
			return(-1)
		}
	}
	
	function getFilefromS3(bucket, key, dir, fileName, cb) {
		console.log("getFilefromS3", bucket, key, dir, fileName)
		// make sure directory exists
		mkdirp.sync(dir)
		
		var params 	= {Bucket: bucket, Key: key}

		var file 	= fs.createWriteStream(fileName);
		file.on('close', function() {
			cb(null);
		})
	    .on('error', function(err){
	         logger.error('download S3 error: ' + filename);
	         cb(err)
	    });
		
		// copy form s3
		try {
			app.s3.headObject(params, function(err, data) {
				if( !err ) {
					app.s3.getObject(params).createReadStream().pipe(file);
					return cb(null)
				} else {
					return cb(err)
				}
			})
		} catch(e) {
			logger.error('S3 error: ', e);
			cb(-1)
		}
	}
	
	function findPixValueFromFile(baseName, regionId, ymd, lat, lon, cb) {		
		if( regionId == 'd03') dx = "ojo-d3"
		if( regionId == 'd02') dx = "ojo-d2"
		if( regionId == 'd07') dx = "ojo-d7"
		
		var dir			= path.join(app.get("tmp_dir"),dx, ymd)
		var fileName 	= path.join(dir, baseName)
		var key			= path.join(ymd, baseName)
		
		debug("findPixValueFromFile", baseName, dir, fileName, key)
			
		try {
			if( fs.existsSync(fileName)) {
				debug("File exists", fileName)
				var result 	= getGeopixValue(fileName, lat, lon)
				cb(null,result)
			} else {
				getFilefromS3(dx, key, dir, fileName, function(err) {
					if( !err ) {
						var result 	= getGeopixValue(fileName, lat, lon)
						cb(null,result)
					} else {
						cb(err, -1)
					}
				})	
			}
		} catch(e) {
			logger.error("findPixValueFromFile Exception", e)
			cb(null, -1)		
		}
	}
	
	function findLandslideNowcast(regionId, ymd, lat, lon, cb) {		
		var baseName	= "landslide_nowcast_"+regionId+"_"+ymd+".tif"
		
		findPixValueFromFile(baseName, regionId, ymd, lat, lon, function(err, result) {
			cb(err, result)
		})
	}
	
	function findDailyPrecip(regionId, ymd, lat, lon, cb) {		
		var baseName	= "trmm_24_"+regionId+"_"+ymd+".tif"
		
		findPixValueFromFile(baseName, regionId, ymd, lat, lon, function(err, result) {
			cb(err, result)
		})
	}
	
	function findForecastIO( regionId, ymd, latitude, longitude, cb) {	
		var options = {
		  exclude: 'currently,minutely,hourly,flags,alerts'
		};
		
		forecast.get(latitude, longitude, options, function (err, res, data) {
			if (err) throw err;
			var today 		= data.daily.data[0]
			var tomorrow 	= data.daily.data[1]
			var result		= [today,tomorrow]
			//console.log('data: ' + util.inspect(data));
			//console.log('result: ' + util.inspect(result));
			cb(err, result)
		});
	}
	
	function QueryAll(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
		if( query != 'location_cast' ) {
			logger.info("QueryLocationCast unsupported query", query)
			return cb(null, null)
		}

		var today		= moment()
		var ymd 		= today.format("YYYYMMDD")
		var yesterday 	= today.subtract(1,'days').format("YYYYMMDD")
		
		// find region of interest
		var region = findRegion(lat, lon)
		if( region == undefined ) {
			logger.error("Undefined region for ", lat, lon)
			return cb(null, null)
		}
		
		var id = regionId( region )
			
		var url = "http://api.tiles.mapbox.com/v4/"+region.map_id+"/"
		url += "pin-m-circle+ff0000("+lon+","+lat+")"
		url += "/" + lon +"," + lat+",10/256x256.png32?access_token="+app.config.mapboxToken
		
		logger.info("QueryLocationcast", limit, region.name, lat, lon)
		
		async.parallel([
			function(callback) {
				findLandslideNowcast(id, ymd, lat, lon, callback) 
			},
			function(callback) {
				findDailyPrecip(id, yesterday, lat, lon, callback) 	// last 24hrs
	
			},
			function(callback) {
				findForecastIO(id, today, lat, lon, callback)
			}
		], function(err, results) {
			var r1 			= results[0]
			var r2			= results[1]
			var r3			= results[2]
			var today, tomorrow;
			
			if( r3 ) {
				today		= r3[0]
				tomorrow 	= r3[1]
			}
			
			var forecastio_attrs = [
				"apparentTemperatureMax", "apparentTemperatureMin",
				"cloudCover", "dewPoint", "humidity","ozone",
				"precipIntensity", "precipIntensityMax", "precipProbability",
				"pressure",	"summary","temperatureMax",	"temperatureMin","windBearing","windSpeed"
			]
			
			debug("landslide/precip results:", r1, r2)
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
					'latitude': {
						'@label': 'latitude',
						'@value': lat
					},
					'longitude': {
						'@label': 'longitude',
						'@value': lon
					},
					'landslide_nowcast': 			{
						"@label": 	'landslide_nowcast',
						"@value": 	r1 
					},
					'landslide_forecast': 			{
						"@label": 	'landslide_forecast',
						"@value": 	0 
					},
					'flood_nowcast': 				{
						"@label": 	'flood_nowcast',
						"@value": 	0 
					},
					'flood_forecast': 				{
						"@label": 	'flood_forecast',
						"@value": 	0 
					},
					'precipitation_last24': 		{
						"@label": 	'precipitation_last24',
						"@value": 	r2 
					},
					'precipitation_nowcast': 		{
						"@label": 	'precipitation_nowcast',
						"@value": 	0
					},
					'precipitation_forecast': 		{
						"@label": 	'precipitation_forecast',
						"@value": 	0 
					},
					'soil_moisture_nowcast': 		{
						"@label": 	'soil_moisture_nowcast',
						"@value": 	0 
					},
					'soil_moisture_forecast': 		{
						"@label": 	'soil_moisture_forecast',
						"@value": 	0 
					}
				}
			}
		
			if( today ) for( var attr in forecastio_attrs ) {
				var attr_name = forecastio_attrs[attr]
				entry.properties[attr_name+"_today"] = {
					"@label": attr_name+"_today",
					"@value": today[attr_name]
				}
			}
			
			if( tomorrow) for( var attr in forecastio_attrs ) {
				var attr_name = forecastio_attrs[attr]
				entry.properties[attr_name+"_tomorrow"] = {
					"@label": attr_name+"_tomorrow",
					"@value": tomorrow[attr_name]
				}
			}
			
			logger.info(entry)
		
			var entries = [entry]
			var json = {
				replies: {
					items: entries
				}
			}
			cb(null, json)	
		})
	}
	
	module.exports.QueryAll 	= QueryAll;
	