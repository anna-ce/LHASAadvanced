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

	var BUCKET  = 'ojo-workshop';

	function padDoy( doy ) {
		if( doy < 10 ) {
			doy = "00"+doy
		} else if( doy < 100 ) {
			doy = "0"+doy
		}
		return doy
	}
	
	function QueryByID(req, user, year, doy, credentials, cb) {
		var products_url 	= host+"/ef5/products/"+year+"/"+doy
		var localdir	 	= app.root+"/../data/ef5/"+year+"/"+doy
		var host 			= "http://"+req.headers.host
		var date			= moment(year+"-"+doy)
		var duration		= 60 * 30
		var id				= year.toString() + doy
		
		function Bewit(url) {
			if( credentials ) {
				var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
				url += "?bewit="+bewit
			}
			return url;
		}
	
		var month = date.month() + 1
		if( month < 10 ) month = "0"+ month
			
		var day		= date.date();
		if( day < 10 ) day = "0"+day
			
		var key =  "ef5" + "/" + date.year() + "/" + doy + "/" +year+month+day+".120000.tif"
		//console.log(key)
		// Check if object exists
		var params = {
			Bucket: BUCKET,
			Key: key
		};
		
		//console.log("Checking", params)
		
		app.s3.headObject(params, function(err, data) {
			if (err) return cb(null,null)
				
			console.log("found", key)
				
			var s3host				= "https://s3.amazonaws.com/ojo-workshop/ef5/"+year + "/" + doy + "/"
			var browse_img_url		= s3host+year+month+day+".120000_thn.jpg"
			var topojson_url		= s3host+year+month+day+".120000_levels.topojson"
			var topojson_file		= s3host+year+month+day+".120000_levels.topojson.gz"
			
			actions = [
				{ 
					"@type": 			"ojo:browse",
					"displayName": 		req.gettext("actions.browse"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/flood_forecast/browse/"+year+"/"+doy),
						"mediaType": 	"html"
					}]
				},
				{
					"@type": 			"ojo:download",
					"displayName": 	req.gettext("actions.download"),
					"using": [
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			Bewit(topojson_url),
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("formats.topojson")
						}
						,{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			Bewit(topojson_url+".gz"),
							"mediaType": 	"application/gzip",
							"displayName": 	req.gettext("formats.topojsongz")
						}	
					]
				},
				{
					"@type": 			"ojo:map",
					"displayName": 	req.gettext("actions.map"),
					"using": [
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"legend",
							"url": 			host+"/mapinfo/flood_forecast/legend",
							"mediaType": 	"text/html",
							"displayName": 	req.gettext("mapinfo.legend")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"style",
							"url": 			host+"/mapinfo/flood_forecast/style",
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("mapinfo.style")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"credits",
							"url": 			host+"/mapinfo/flood_forecast/credits",
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("mapinfo.credits")
						}
					]
				}
			]
			
			var source 		= req.gettext("sources.ef5")
			var sensor 		= req.gettext("sensors.ef5")
	
			var properties = {
					"source": {
						"@label": req.gettext("properties.source"),
						"@value": source
					},
					"sensor": {
						"@label": req.gettext("properties.sensor"),
						"@value": sensor
					},
					"date": {
						"@label": req.gettext("properties.date"),
						"@value": date.format(req.gettext("formats.date"))
					},
					"resolution": {
						"@label": req.gettext("properties.resolution"),
						"@value": "400m"
					}
					
			}
				
			var entry = {
				"@id": 			id,
				"@type": 		"geoss:flood_forecast",
				"displayName": 	id,
				"image": 		[ 
									{
										"url": browse_img_url,
										"mediaType": "image/png",
										"rel": "browse"
									}
								],
				"properties": 		properties,
				"geometry": {
					"type": "Polygon",
					"coordinates": [[
						[11.0249996, -30.0833340],
						[11.0249996, -12.0833330],
						[26.5250004, -12.0833330],
						[26.5250004, -30.0833340],
						[11.0249996, -30.0833340]
					]]
				},
				"action": 			actions
			}
			//console.log("entry done")
			cb(null,entry)
		})
	}
	
	function check( req, user, d, startTime, endTime, credentials, entries, callback ) {
		time				= endTime.clone()
		time	 			= time.subtract(d, "days");
	
		var year 			= time.year();
		var doy  			= padDoy(time.dayOfYear());
			
		QueryByID(req, user, year, doy, credentials, function(err, data) {
			if( !err && data) entries.push(data)
			callback(null)
		})
	}

	
	function Query(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
		
		if( query != 'flood_forecast') {
			//logger.info("unsupported query", query)
			return cb(null, null)
		}

		//if( bbox && !ValidateBBox(bbox)) {
		//	logger.error("invalid bbox", bbox)
		//	return cb(null, null)
		//}
	
		if( startTime && !startTime.isValid()) {
			logger.error("Invalid start time: "+ startTime)
			return cb(null, null)
		}
	
		if( endTime && !endTime.isValid()) {
			logger.error( "Invalid end time: "+ endTime)
			return cb(null, null)
		}
	
		if( startIndex && startIndex < 0 ) {
			logger.error("Invalid startIndex: "+startIndex)			
			return cb(null, null)	
		}
	
		if( itemsPerPage && itemsPerPage < 0 ) {
			logger.error("Invalid itemsPerPage: "+itemsPerPage)			
			return cb(null, null)		
		}
	
		if( lat && (lat < -21 || lat>-12) ) {
			return cb(null, null)	
		}
	
		if( lon && (lon < 15 || lon>23) ) {
			return cb(null, null)		
		}
			
		if( bbox ) {
			lon = (bbox[0]+bbox[2])/2
			lat = (bbox[1]+bbox[3])/2
		}
		
		// we only have one scene here... we can fix this later
		var days = []
		itemsPerPage = limit;
		for( var i=0; i<itemsPerPage; i++ ) {
			days.push(i)
		}
	
		entries		= []
	
		async.each(days, function(d, callback) {
			if( entries.length < limit ) {
				check( req, user, d, startTime, endTime, credentials, entries, callback )
			} else {
				callback(null, null)
			} 
		}, function(err) {
			//console.log("Modis LST Done", err, entries.length)
			var json = {
				replies: {
					items: entries
				}
			}
			//console.log("query_ef5 done")
			cb(null, json)	
		})
	}
	
	
	module.exports.Query	 	= Query;
	module.exports.QueryByID 	= QueryByID;
	