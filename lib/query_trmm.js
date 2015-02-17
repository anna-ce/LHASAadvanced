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

// ===================================================
// 24hr Daily Precip Product

function TRMMProductId(region, ymd) {
	return "trmm_24_"+regionId(region)+"_"+ymd
}

//
// Do we have that object in S3?
//
function findTRMMProduct(region, ymd, cb ) {
	var trmmid 	= TRMMProductId(region, ymd)
	var params = {
	  Bucket: region.bucket,
	  Key: path.join(ymd, trmmid + ".topojson.gz")
	}
	
	app.s3.headObject(params, function(err, data) {		
		//console.log("s3 head", params, err)
		if( err ) {
			cb(err, -1)
		} else {
			cb(null, data.ContentLength)
		}
	})
}

function BboxToPolygon(bbox) {
	var minlon = bbox[0]
	var minlat = bbox[1]
	var maxlon = bbox[2]
	var maxlat = bbox[3]
	str = "[["
		str += "["+minlon+", "+minlat+"],"
		str += "["+minlon+", "+maxlat+"],"
		str += "["+maxlon+", "+maxlat+"],"
		str += "["+maxlon+", "+minlat+"],"
	str += "]]"
	return str
}

function checkTRMM( req, user, ymd, region, credentials, callback ) {
	//console.log("checkTRMM", ymd)
	var tmp_dir 		= app.get("tmp_dir")
	var user			= req.session.user
	var host			= req.protocol + "://" + req.headers.host
	var originalUrl		= host + req.originalUrl

	findTRMMProduct(region, ymd, function(err, contentLength) {
		if( !err ) {
			//console.log("found trmm product")
			var duration		= 60 * 30
			var credentials		= req.session.credentials
			
			function Bewit(url) {
				var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
				url += "?bewit="+bewit
				return url;
			}
			
			var base_url = host+"/products/"+regionId(region)+"/"+ymd+"/"+TRMMProductId(region, ymd)
				
			var date 	= moment(ymd, "YYYYMMDD")
			var source	= "NASA GSFC"
			var sensor	= "TRMM";
			
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
					"size": {
						"@label": req.gettext("properties.size"),
						"@value": filesize(contentLength)
					},
					"resolution": {
						"@label": req.gettext("properties.resolution"),
						"@value": "~1km from 0.25deg"
					},
					"geometry": {
						"type": "Polygon",
						"coordinates": BboxToPolygon(region.bbox)
					}
			}				
			
			var entry = {
				"@id": 	TRMMProductId(region, ymd),
				"@type": "geoss:daily_precipitation",
				"image": [
					{
						"url": base_url+".thn.png",
						"mediaType": "image/png",
						"rel": "browse"
					}
				],
				"properties": properties,
				"action": [
						{
							"@type": 			"ojo:download",
							"displayName": 		req.gettext("actions.download"),
							"using": [{
								"@type": 		"as:HttpRequest",
								"method": 		"GET",
								"url": 			Bewit(base_url+".topojson.gz"),
								"mediaType": 	"application/x-gzip",
								"size": 		contentLength,
								"displayName": 	req.gettext("formats.topojsongz")
							},
							{
								"@type": 		"as:HttpRequest",
								"method": 		"GET",
								"url": 			Bewit(base_url+".topojson"),
								"mediaType": 	"application/json",
								"displayName": 	req.gettext("formats.topojson")
							}]								
						},
						{
							"@type": 			"ojo:map",
							"displayName": 		req.gettext("actions.map"),
							"using": [
								{
									"@type": 		"as:HttpRequest",
									"method": 		"GET",
									"@id": 			"legend",
									"url": 			host+"/mapinfo/trmm_24/legend",
									"mediaType": 	"text/html",
									"displayName": 	req.gettext("mapinfo.legend")
								},
								{
									"@type": 		"as:HttpRequest",
									"method": 		"GET",
									"@id": 			"style",
									"url": 			host+"/mapinfo/trmm_24/style",
									"mediaType": 	"application/json",
									"displayName": 	req.gettext("mapinfo.style")
								},
								{
									"@type": 		"as:HttpRequest",
									"method": 		"GET",
									"@id": 			"credits",
									"url": 			host+"/mapinfo/trmm_24/credits",
									"mediaType": 	"application/json",
									"displayName": 	req.gettext("mapinfo.credits")
								}
							]
						},
						{ 
							"@type": 			"ojo:browse",
							"displayName": 		req.gettext("actions.browse"),
							"using": [{
								"@type": 		"as:HttpRequest",
								"method": 		"GET",
								"url": 			base_url+".html",
								"mediaType": 	"html",
							}]
						}
				]
			}
			//console.log(entry)
			entries.push(entry)
			callback(null)
		} else {
			//logger.error("Error getting TRMM", ymd)
			callback(null)	
		}
	})
}

function QueryTRMM(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
	if( query != 'daily_precipitation' ) {
		logger.error("unsupported query", query)
		return cb(null, null)
	}

	// find region of interest
	var region = findRegion(lat, lon)
	if( region === undefined ) {
		logger.error("Undefined region for ", lat, lon)
		return cb(null, null)
	}
	
	if( user == undefined ) {
		logger.error("undefined user for query")
		return cb(null, null)
	}
	
	entries	= []
	async.whilst( 
		function() {
			if( entries.length >= limit) {
				//console.log("over entry limit", entries.length)
				return false
			}
				
			if( !endTime.isAfter(startTime) || startTime.isSame(endTime)) {
				//console.log("over time limit", endTime.isAfter(startTime), startTime.isSame(endTime))
				return false
			} 
			return true
		},
		function(callback) {
			var ymd = endTime.format("YYYYMMDD")
		
			checkTRMM( req, user, ymd, region, credentials, callback )
			endTime.subtract('days', 1);
		},
		function(err) {	
			//console.log("TRMM Done", err, entries.length)
			var json = {
				replies: {
					items: entries
				}
			}
			cb(null, json)	
		}
	)
}

module.exports.QueryTRMM	= QueryTRMM;
//module.exports.QueryByID 	= QueryByID;
