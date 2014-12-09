var util	= require('util'),
	async	= require('async'),
	eyes	= require('eyes'),
	moment	= require('moment'),
	path	= require('path'),
	mkdirp 	= require('mkdirp'),
	filesize = require('filesize'),
	Hawk	= require('hawk'),
	glob 	= require("glob")
	debug	= require('debug')('products'),
	sys 	= require('sys'),
	exec 	= require('child_process').exec,
	mime	= require('mime-types'),
	osm_geojson	= require("osm-and-geojson/osm_geojson"),
	tokml	= require('tokml'),
	fs		= require('fs');
	
	mime.define( {
		"application/x-osm+xml": [ "osm"],
		"application/json": [ "geojson", "topojson"],
		"application/x-gzip": ["gz"]
	})
	
	function puts(error, stdout, stderr) { sys.puts(stdout) }
	
	function InBBOX( lat, lon, bbox) {
		if( (lat > bbox[2]) && (lat< bbox[3]) && (lon > bbox[0]) && (lon < bbox[2]) ) return true;
		return false
	}
	
	function findRegion(lat, lon) {
		if( InBBOX(lat, lon, app.config.regions.d02.bbox)) return app.config.regions.d02
		if( InBBOX(lat, lon, app.config.regions.d03.bbox)) return app.config.regions.d03
		return undefined
	}
	
	// Check if file exists on S3, if yes, download it into /tmp
	function existsOnS3(bucket, folder, fname, cb ) {
		var tmp_dir = app.get("tmp_dir")
		
		console.log("Check on S3", bucket, folder, fname)
		var options = {
			Bucket: bucket, 
			Key: folder + "/" + fname
		};
		app.s3.getObject( options, function(err, data) {
			if( !err ) {
				var dir = path.join(tmp_dir, bucket, folder)
				
				// make sure folder exists
				mkdirp.sync(dir)
				
				var fileName	= path.join(dir, fname)
				var out 		= fs.createWriteStream(fileName)	
				var buff 		= new Buffer(data.Body, "binary")
				var Readable 	= require('stream').Readable;
				var rs 			= new Readable;
				rs.push(buff)
				rs.push(null)
				rs.pipe(out)
				
			} else {
				console.log("NOT Found it on S3", fname)
			}
			cb(err)
		})
	}
	
	function sendFile( res, file ) {
		var ext 		= path.extname(file)
		var basename 	= 	path.basename(file)
		var dirname 	= 	path.dirname(file)
		
		var mime_type = mime.lookup(path.basename(file))
		
		if( basename.indexOf(".topojson") > 0) {
			res.header("Content-Type", "application/json")
			res.header("Content-Encoding", "gzip")
			console.log("sending .topojson application/json gzip", basename)
		} else {
			console.log("sending ", mime_type, basename, dirname)
			res.header("Content-Type", mime_type, basename)
			console.log(ext, mime_type, "no encoding")
		}
		
		res.header("Access-Control-Allow-Origin", "*")
		res.sendfile(basename, {root: dirname})
	}
	
	function regionId( region ) {
		var dx = "d03"
		if( region === app.config.regions.d02 ) dx = "d02"
		return dx
	}
	
	function sendLocationProducts(req, res ) {
        var lat    = req.query.lat
        var lon    = req.query.lon
        var user    = req.session.user
        
        if( user == undefined ) return res.send(400, "invalid user")
        
        // validate lat/lon
        if( lat < -90 || lat > 90 ) return res.send(400, "invalid latitude")
        if( lon < -180 || lat > 180 ) return res.send(400, "invalid longitude")
        
        var region      = findRegion(lat,lon)
        if( region == undefined ) {
            logger.error("invalid region", lat, lon)
            return res.send(400)
        }
        
        var json = {
            "type": "FeatureCollection",
            "features": [
                { "type": "Feature",
                "properties": {
                    "source":   "NASA GSFC",
                    "date":     moment().format("YYY-MM-DD"),
                    "landslide_nowcast":        1,
                    "landslide_forecast":       2,
                    "flood_nowcast":            2,
                    "flood_forecast":           3,
                    "precipitation_nowcast":    15,
                    "precipitation_forecast":   23,
                    "soil_moisture_nowcast":    2.5,
                    "soil_moisture_forecast":   5.3,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [ user.longitude, user.latitude ]
                }}
            ]
        }
        console.log("sendLocationProducts", json)
        res.send(json)
	}
    
	// ===================================================
	// Landslide Nowcast Product

	function LandslideNowcastProductId(region, ymd) {
		return "landslide_nowcast_"+regionId(region)+"_"+ymd
	}
	
	function findLandslideNowcastProduct(region, ymd, cb ) {
		var tmp_dir 	= app.get("tmp_dir")
		var trmmid 		= LandslideNowcastProductId(region, ymd)
		var fileName 	= path.join(tmp_dir, region.bucket, ymd, trmmid + ".topojson.gz")
		fs.exists(fileName, function(err) {
			if( err ) {
				cb(false)
			} else {
				cb(true)
			}
		})
	}

	function sendLandslideNowcastProducts(query, region, ymds, limit, req, res ) {
		var tmp_dir 		= app.get("tmp_dir")
		
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		var results 		= []
	
		async.each( ymds, function(ymd, cb) {
			// check if we have a product for that region and date
			findLandslideNowcastProduct(region, ymd, function(err) {
				if( !err ) {
					// add product entry to result
					var topojsonFile	= path.join(tmp_dir, region.bucket, ymd, LandslideNowcastProductId(region, ymd)+".topojson.gz")
					var stats 			= fs.statSync( topojsonFile )
					
					var duration		= 60 * 30
					var credentials		= req.session.credentials
					
					function Bewit(url) {
						var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
						url += "?bewit="+bewit
						return url;
					}
					
					var base_url = host+"/products/"+regionId(region)+"/"+ymd+"/"+LandslideNowcastProductId(region, ymd)
					var entry = {
						"id": LandslideNowcastProductId(region, ymd),
						"image": [
							{
								"url": base_url+".thn.png",
								"mediaType": "image/png",
								"rel": "browse"
							}
						],
						"properties": {
							"source": 	"NASA GSFC",
							"sensor": 	"LandslideModel",
							"date": 	moment(ymd, "YYYYMMDD").format("YYYY-MM-DD"),
							"bbox": 	region.bbox,
							"size": 	filesize(stats.size)
						},
						"actions": {
							"download": [
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".topojson.gz"),
									"mediaType": 	"application/json",
									"displayName": 	"topojson",
									"size": 		stats.size
								}
							],
							"view": 	base_url+".html",
							"share": 	base_url+".html",
							"map": [
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"landslide_nowcast_legend",
									"method": 		"GET",
									"url": 			host+"/mapinfo/landslide_nowcast/legend",
									"mediaType": 	"test/html",
									"displayName": 	"legend",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"landslide_nowcast_style",
									"method": 		"GET",
									"url": 			host+"/mapinfo/landslide_nowcast/style",
									"mediaType": 	"application/json",
									"displayName": 	"style",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"landslide_nowcast_credits",
									"method": 		"GET",
									"url": 			host+"/mapinfo/landslide_nowcast/credits",
									"mediaType": 	"application/json",
									"displayName": 	"credits",
								}
							]
						}
					}
					results.push(entry)
					if( results.length >= limit ) return cb(-1)
				}
				cb(null)
			}) 
		}, function(err) {
			res.set("Access-Control-Allow-Origin", "*")
			var json = {
				"objectType": query,
				"id": "urn:trmm:"+query,
				"displayName": "Landslide Nowcast",
				"replies": {
					"url": originalUrl,
					"mediaType": "application/activity+json",
					"totalItems": results.length,
					"items": results
				}
			}
			res.send(json)
		})				
	}
	
	// ===================================================
	// 24hr Daily Precip Product
	
	function TRMMProductId(region, ymd) {
		return "trmm_24_"+regionId(region)+"_"+ymd
	}
	
	function findTRMMProduct(region, ymd, cb ) {
		var tmp_dir 	= app.get("tmp_dir")
		var trmmid 		= TRMMProductId(region, ymd)
		var fileName 	= path.join(tmp_dir, region.bucket, ymd, trmmid + ".topojson.gz")
		fs.exists(fileName, function(err) {
			if( err ) {
				cb(false)
			} else {
				cb(true)
			}
		})
	}
	
	function sendTRMMProducts(query, region, ymds, limit, req, res ) {
		var tmp_dir 		= app.get("tmp_dir")
		
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		var results 		= []
	
		async.each( ymds, function(ymd, cb) {
			// check if we have a product for that region and date
			findTRMMProduct(region, ymd, function(err) {
				if( !err ) {
					// add product entry to result
					var topojsonFile	= path.join(tmp_dir, region.bucket, ymd, TRMMProductId(region, ymd)+".topojson.gz")
					var stats 			= fs.statSync( topojsonFile )
					
					var duration		= 60 * 30
					var credentials		= req.session.credentials
					
					function Bewit(url) {
						var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
						url += "?bewit="+bewit
						return url;
					}
					
					var base_url = host+"/products/"+regionId(region)+"/"+ymd+"/"+TRMMProductId(region, ymd)
					var entry = {
						"id": TRMMProductId(region, ymd),
						"image": [
							{
								"url": base_url+".thn.png",
								"mediaType": "image/png",
								"rel": "browse"
							}
						],
						"properties": {
							"source": 	"NASA GSFC",
							"sensor": 	"TRMM",
							"date": 	moment(ymd, "YYYYMMDD").format("YYYY-MM-DD"),
							"bbox": 	region.bbox,
							"size": 	filesize(stats.size)
						},
						"actions": {
							"download": [
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".topojson.gz"),
									"mediaType": 	"application/json",
									"displayName": 	"topojson",
									"size": 		stats.size
								}
							],
							"view": 	base_url+".html",
							"share": 	base_url+".html",
							"map": [
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"trmm_24_legend",
									"method": 		"GET",
									"url": 			host+"/mapinfo/trmm_24/legend",
									"mediaType": 	"test/html",
									"displayName": 	"legend",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"trmm_24_style",
									"method": 		"GET",
									"url": 			host+"/mapinfo/trmm_24/style",
									"mediaType": 	"application/json",
									"displayName": 	"style",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"trmm_24_credits",
									"method": 		"GET",
									"url": 			host+"/mapinfo/trmm_24/credits",
									"mediaType": 	"application/json",
									"displayName": 	"credits",
								}
							]
						}
					}
					results.push(entry)
					if( results.length >= limit ) return cb(-1)
				}
				cb(null)
			}) 
		}, function(err) {
			res.set("Access-Control-Allow-Origin", "*")
			var json = {
				"objectType": query,
				"id": "urn:trmm:"+query,
				"displayName": "Daily Precipitation",
				"replies": {
					"url": originalUrl,
					"mediaType": "application/activity+json",
					"totalItems": results.length,
					"items": results
				}
			}
			res.send(json)
		})				
	}
	
	function WrfProductId(region, ymd) {
		return "wrf_24_"+regionId(region)+"_"+ymd
	}
	
	function findWrfProduct(region, ymd, cb ) {
		var tmp_dir 	= app.get("tmp_dir")
		
		var id 			= WrfProductId(region, ymd)
		var fileName 	= path.join(tmp_dir, region.bucket, ymd, id + ".topojson.gz")
		fs.exists(fileName, function(err) {
			if( err ) {
				cb(false)
			} else {
				cb(true)
			}
		})
	}
	
	function sendWrfProducts(query, region, ymds, limit, req, res ) {
		var tmp_dir 		= app.get("tmp_dir")
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		var results 		= []
		console.log("Looking for WRF products...")
		async.each( ymds, function(ymd, cb) {
			// check if we have a product for that region and date
			findWrfProduct(region, ymd, function(err) {
				if( !err ) {
					// add product entry to result
					var topojsonFile	= path.join(tmp_dir, region.bucket, ymd, WrfProductId(region, ymd)+".topojson.gz")
					var stats 			= fs.statSync( topojsonFile )
					
					var duration		= 60 * 30
					var credentials		= req.session.credentials
					
					function Bewit(url) {
						var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
						url += "?bewit="+bewit
						return url;
					}
					
					var base_url = host+"/products/"+regionId(region)+"/"+ymd+"/"+WrfProductId(region, ymd)
					var entry = {
						"id": WrfProductId(region, ymd),
						"image": [
							{
								"url": base_url+".thn.png",
								"mediaType": "image/png",
								"rel": "browse"
							}
						],
						"properties": {
							"source": 	"NASA MSFC",
							"sensor": 	"WRF",
							"date": 	moment(ymd, "YYYYMMDD").format("YYYY-MM-DD"),
							"bbox": 	region.bbox,
							"size": 	filesize(stats.size)
						},
						"actions": {
							"download": [
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".topojson.gz"),
									"mediaType": 	"application/json",
									"displayName": 	"topojson",
									"size": 		stats.size
								}
							],
							"view": 	base_url+".html",
							"share": 	base_url+".html",
							"map": [
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"wrf_24_legend",
									"method": 		"GET",
									"url": 			host+"/mapinfo/wrf_24/legend",
									"mediaType": 	"test/html",
									"displayName": 	"legend",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"wrf_24_style",
									"method": 		"GET",
									"url": 			host+"/mapinfo/wrf_24/style",
									"mediaType": 	"application/json",
									"displayName": 	"style",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"wrf_24_credits",
									"method": 		"GET",
									"url": 			host+"/mapinfo/wrf_24/credits",
									"mediaType": 	"application/json",
									"displayName": 	"credits",
								}
							]
						}
					}
					results.push(entry)
					if( results.length >= limit ) return cb(-1)
				}
				cb(null)
			}) 
		}, function(err) {
			res.set("Access-Control-Allow-Origin", "*")
			var json = {
				"objectType": query,
				"id": "urn:trmm:"+query,
				"displayName": "Total Precipitation 24hr Forecast",
				"replies": {
					"url": originalUrl,
					"mediaType": "application/activity+json",
					"totalItems": results.length,
					"items": results
				}
			}
			res.send(json)
		})				
	}
	
	function GFMSProductId(region, ymd) {
		return "gfms_24_"+regionId(region)+"_"+ymd
	}
	
	function findGFMSProduct(region, ymd, cb ) {
		var tmp_dir 	= app.get("tmp_dir")
		
		var id 			= GFMSProductId(region, ymd)
		var fileName 	= path.join(tmp_dir, region.bucket, ymd, id + ".topojson.gz")
		fs.exists(fileName, function(err) {
			if( err ) {
				cb(false)
			} else {
				cb(true)
			}
		})
	}
	
	function sendGFMSProducts(query, region, ymds, limit, req, res ) {
		var tmp_dir 		= app.get("tmp_dir")
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		var results 		= []
		console.log("Looking for GFMS products...")
		async.each( ymds, function(ymd, cb) {
			// check if we have a product for that region and date
			findGFMSProduct(region, ymd, function(err) {
				if( !err ) {
					// add product entry to result
					var topojsonFile	= path.join(tmp_dir, region.bucket, ymd, GFMSProductId(region, ymd)+".topojson.gz")
					var stats 			= fs.statSync( topojsonFile )
					
					var duration		= 60 * 30
					var credentials		= req.session.credentials
					
					function Bewit(url) {
						var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
						url += "?bewit="+bewit
						return url;
					}
					
					var base_url = host+"/products/"+regionId(region)+"/"+ymd+"/"+GFMSProductId(region, ymd)
					var entry = {
						"id": GFMSProductId(region, ymd),
						"image": [
							{
								"url": base_url+".thn.png",
								"mediaType": "image/png",
								"rel": "browse"
							}
						],
						"properties": {
							"source": 	"UMD",
							"sensor": 	"GFMS",
							"date": 	moment(ymd, "YYYYMMDD").format("YYYY-MM-DD"),
							"bbox": 	region.bbox,
							"size": 	filesize(stats.size)
						},
						"actions": {
							"download": [
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".topojson.gz"),
									"mediaType": 	"application/json",
									"displayName": 	"topojson",
									"size": 		stats.size
								}
							],
							"view": 	base_url+".html",
							"share": 	base_url+".html",
							"map": [
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"gfms_24_legend",
									"method": 		"GET",
									"url": 			host+"/mapinfo/gfms_24/legend",
									"mediaType": 	"test/html",
									"displayName": 	"legend",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"gfms_24_style",
									"method": 		"GET",
									"url": 			host+"/mapinfo/gfms_24/style",
									"mediaType": 	"application/json",
									"displayName": 	"style",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"gfms_24_credits",
									"method": 		"GET",
									"url": 			host+"/mapinfo/gfms_24/credits",
									"mediaType": 	"application/json",
									"displayName": 	"credits",
								}
							]
						}
					}
					results.push(entry)
					if( results.length >= limit ) return cb(-1)
				}
				cb(null)
			}) 
		}, function(err) {
			res.set("Access-Control-Allow-Origin", "*")
			var json = {
				"objectType": query,
				"id": "urn:trmm:"+query,
				"displayName": "Flood Forecast",
				"replies": {
					"url": originalUrl,
					"mediaType": "application/activity+json",
					"totalItems": results.length,
					"items": results
				}
			}
			res.send(json)
		})				
	}
		
	function EO1ProductId(fileName) {
		return path.basename(fileName, ".topojson.gz")
	}
		
	function findEO1Product(region, ymd, cb ) {
		var tmp_dir 	= app.get("tmp_dir")
		
		var dirName 	= path.join(tmp_dir, region.bucket, ymd, "EO1A*.topojson.gz")
		//console.log(dirName)
		// glob for EO1A
		glob( dirName, function (err, files) {
			if( !err && files.length > 0 ) {
				cb(null, files)
			} else {
				cb(-1)				
			}
		})
	}
	// localhost:7465/products/opensearch?q=surface_water&lat=18.58&lon=-72.36&startTime=2012-04-28&endTime=2012-12-28
	function sendEO1Products(query, region, ymds, limit, req, res ) {
		var tmp_dir 		= app.get("tmp_dir")
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		var results 		= []
		console.log("Looking for EO1 products...")
		async.each( ymds, function(ymd, cb) {
			// check if we have a product for that region and date
			findEO1Product(region, ymd, function(err, files) {
				if( !err ) {
					var fileName = path.basename(files[0])
					// add product entry to result
					var topojsonFile	= path.join(tmp_dir, region.bucket, ymd, fileName)
					var stats 			= fs.statSync( topojsonFile )
					
					var duration		= 60 * 30
					var credentials		= req.session.credentials
					
					function Bewit(url) {
						var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
						url += "?bewit="+bewit
						return url;
					}
					
					var base_url = host+"/products/"+regionId(region)+"/"+ymd+"/"+EO1ProductId(fileName)
					var entry = {
						"id": EO1ProductId(fileName),
						"image": [
							{
								"url": base_url+".thn.png",
								"mediaType": "image/png",
								"rel": "browse"
							}
						],
						"properties": {
							"source": 	"USGS",
							"sensor": 	"EO-1",
							"date": 	moment(ymd, "YYYYMMDD").format("YYYY-MM-DD"),
							"bbox": 	region.bbox,
							"size": 	filesize(stats.size)
						},
						"actions": {
							"download": [
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".topojson"),
									"mediaType": 	"application/json",
									"displayName": 	"topojson"
								},
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".topojson.gz"),
									"mediaType": 	"application/gzip",
									"displayName": 	"topojson.gz",
									"size": 		filesize(stats.size)
								},
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".geojson"),
									"mediaType": 	"application/json",
									"displayName": 	"geojson"
								},
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".kml"),
									"mediaType": 	"application/vnd.google-earth.kml+xml",
									"displayName": 	"kml"
								},
								{
									"objectType": 	"HttpActionHandler",
									"method": 		"GET",
									"url": 			Bewit(base_url+".osm"),
									"mediaType": 	"application/xml",
									"displayName": 	"osm"
								}
								
							],
							"view": 	base_url+".html",
							"share": 	base_url+".html",
							"map": [
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"gfms_24_legend",
									"method": 		"GET",
									"url": 			host+"/mapinfo/eo1/legend",
									"mediaType": 	"text/html",
									"displayName": 	"legend",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"gfms_24_style",
									"method": 		"GET",
									"url": 			host+"/mapinfo/eo1/style",
									"mediaType": 	"application/json",
									"displayName": 	"style",
								},
								{
									"objectType": 	"HttpActionHandler",
									"id": 			"gfms_24_credits",
									"method": 		"GET",
									"url": 			host+"/mapinfo/eo1/credits",
									"mediaType": 	"application/json",
									"displayName": 	"credits",
								}
							]
						}
					}
					results.push(entry)
					if( results.length >= limit ) return cb(-1)
				}
				cb(null)
			}) 
		}, function(err) {
			res.set("Access-Control-Allow-Origin", "*")
			var json = {
				"objectType": query,
				"id": "urn:trmm:"+query,
				"displayName": "Flood Forecast",
				"replies": {
					"url": originalUrl,
					"mediaType": "application/activity+json",
					"totalItems": results.length,
					"items": results
				}
			}
			res.send(json)
		})				
	}

module.exports = {
	// http://localhost:7465/products/opensearch?q=daily_precipitation&lat=18&lon=-70&startTime=20140418&endTime=20140421
	
	opensearch: function(req, res) {
		var query 			= req.query.q
		var bbox			= req.query.bbox ? req.query.bbox.split(",").map(parseFloat) : undefined
		var itemsPerPage	= req.query.itemsPerPage || 7
		var startIndex		= req.query.startIndex || 1
		var limit			= req.query.limit || 25
		var startTime		= req.query.startTime ? moment(req.query.startTime, "YYYY-MM-DD") : moment()
		var endTime			= req.query.endTime ? moment(req.query.endTime, "YYYY-MM-DD") : moment()
		var lat				= req.query.lat ? parseFloat(req.query.lat) : undefined
		var lon				= req.query.lon ? parseFloat(req.query.lon) : undefined
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		
		console.log("Product opensearch", originalUrl)
		
		if( bbox ) {
			lon = (bbox[0]+bbox[2])/2.0
			lat = (bbox[1]+bbox[3])/2.0
		}
		
		var results = []
		var json = {
			"objectType": query,
			"id": "urn:trmm:"+query,
			"displayName": "Daily Precipitation",
			"replies": {
				"url": originalUrl,
				"mediaType": "application/activity+json",
				"totalItems": results.length,
				"items": results
			}
		}
		
		// This for products we support
		if( (query != 'daily_precipitation') && 
			(query != "daily_precipitation_24h_forecast") && 
			(query != "flood_nowcast") && 
			(query != "surface_water") &&
			(query != "landslide_nowcast") &&
            (query != "location_cast")
		) {
			console.log("Invalid product", query)
			return res.send(json)
		}
		
		// find region of interest
		var region = findRegion(lat, lon)
		if( region === undefined ) {
			console.log("Undefined region for ", lat, lon)
			return res.send( json )
		}
			
		var ymds = []
		while( endTime.isAfter(startTime) || startTime.isSame(endTime)) {
			var ymd = endTime.format("YYYYMMDD")
			ymds.push(ymd)
			endTime.subtract('days', 1);
		}
		
		console.log("Searching for", query)
		if( query == 'location_cast') {
			sendLocationProducts(req, res )            
    	} else if( query == 'daily_precipitation') {
			sendTRMMProducts(query, region, ymds, limit, req, res )
		} else if( query == 'daily_precipitation_24h_forecast') {
			sendWrfProducts(query, region, ymds, limit, req, res )
		} else if( query == 'flood_nowcast') {
			sendGFMSProducts(query, region, ymds, limit, req, res )
		} else if( query == 'surface_water') {
			sendEO1Products(query, region, ymds, limit, req, res )
		} else if( query == 'landslide_nowcast') {
			sendLandslideNowcastProducts(query, region, ymds, limit, req, res )
		}
	},
	
	index: function(req, res) {
		var user = req.session.user
		res.render("products/index", {user: user})
	},
	
	distribute: function(req, res) {
		var reg_id 	= req.params.region
		var ymd		= req.params.ymd
		var id		= req.params.id
		var fmt		= req.params.fmt || 'html'
		var tmp_dir = app.get("tmp_dir")
		
		var host	= req.headers.host
		var url		= req.protocol+"://"+host + "/products/"+reg_id+"/"+ymd+"/"+id+"."+fmt
		
		var region;
		
		switch(reg_id) {
			case 'd02':
				region = app.config.regions.d02
				break;
			case 'd03':
				region = app.config.regions.d03
				break;
			default:
				return res.send("Invalid Region", 401)
		}
		
		//console.log("Headers", req.headers)
		console.log("Products", reg_id, ymd, id, fmt)
		
		var pathName	= tmp_dir+"/"+region.bucket+"/"+ymd
		var file 		= path.join( pathName, id+"."+fmt )
		
		switch(fmt) {
			case 'html':
				var fbAppId 	= app.config.fbAppId;
				var fname		= id //+ "_"+reg_id+"_"+ymd
				var image 		= req.protocol + "://" + host +"/products/" + reg_id + "/" + ymd + "/" + fname + ".thn.png"
				var topojson 	= req.protocol + "://" + host +"/products/" + reg_id + "/" + ymd + "/" + fname + ".topojson.gz"
				
				if( id.indexOf('trmm_24') >= 0 ) {
					var date = moment(ymd, "YYYYMMDD")
					
					res.render("products/trmm", {
						layout: 		false,
						image: 			image,
						fbAppId: 		fbAppId,
						description: 	"TRMM daily accumulated precipitation for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
						date: 			date.format("YYYY-MM-DD"),
						id: 			id,
						ymd: 			ymd, 
						region:  		region,
						reg_id: 		reg_id,
						fname: 			fname+".topojson.gz",
						url: 		 	url,
						topojson: 		topojson
					})
				} else if( id.indexOf('landslide_nowcast') >= 0 ) {
					var date = moment(ymd, "YYYYMMDD")
					
					res.render("products/landslidenowcast", {
						layout: 		false,
						image: 			image,
						fbAppId: 		fbAppId,
						description: 	"Landslide Nowcast for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
						date: 			date.format("YYYY-MM-DD"),
						id: 			id,
						ymd: 			ymd, 
						region:  		region,
						reg_id: 		reg_id,
						fname: 			fname+".topojson.gz",
						url: 		 	url,
						topojson: 		topojson
					})
				} else if(id.indexOf('wrf_') >= 0) {
					var date = moment(ymd, "YYYYMMDD")
										
					res.render("products/wrf", {
						layout: 		false,
						image: 			image,
						fbAppId: 		fbAppId,
						description: 	"WRF Forecast Precipitation for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
						date: 			date.format("YYYY-MM-DD"),
						id: 			id,
						region:  		region,
						url: 		 	url,
						topojson: 		topojson
					})
					
				} else if(id.indexOf('gfms_') >= 0) {
					var date = moment(ymd, "YYYYMMDD")
										
					res.render("products/gmfs", {
						layout: 		false,
						image: 			image,
						fbAppId: 		fbAppId,
						description: 	"Flood Nowcast for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
						date: 			date.format("YYYY-MM-DD"),
						id: 			id,
						region:  		region,
						url: 		 	url,
						topojson: 		topojson
					})
				} else if(id.indexOf('EO1A') >= 0) {
					var date = moment(ymd, "YYYYMMDD")
										
					res.render("products/eo1", {
						layout: 		false,
						image: 			image,
						fbAppId: 		fbAppId,
						description: 	"EO1 Surface Water Product for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
						date: 			date.format("YYYY-MM-DD"),
						id: 			id,
						region:  		region,
						url: 		 	url,
						topojson: 		topojson
					})
					
				} else {
					res.send("Unknown file/id:"+id)
				}
				break;
				
			case 'topojson':
				var acceptEncoding = req.headers['accept-encoding']
				//console.log('topojson requested header:', req.headers)
				if( acceptEncoding.indexOf('gzip') < 0) {
					console.log("does not accept gzip... we need to expand topojson...")
				}
				file += ".gz"
				
			case 'gz':
				if( fs.existsSync(file)) {
					sendFile(res, file)
				} else {
					// Check on S3
					existsOnS3(region.bucket, ymd, path.basename(file), function(err) {
						if(!err) {
							sendFile( res, file )
						} else {
							res.send(404, "file not found")
						}
					})
				}
				break
			
			case 'osm':
				// fall through
			case 'kml':
				// fall through
			case 'geojson':
				
				// We need to make it up if it does not exists
				if( fs.existsSync(file)) {
					sendFile( res, file )
				} else {
					
					var topojsonFile 	= path.join(pathName, id + ".topojson")
					var geojsonFile 	= path.join(pathName, id + ".geojson")
											
					function create_topojson(cb) {
						// TopoJson file
						if( ! fs.existsSync(topojsonFile)) {
							console.log("topojson file does not exists", topojsonFile)
							var cmd = "gunzip -c "+ topojsonFile+".gz > " + topojsonFile
							console.log(cmd)
							exec(cmd, function (error, stdout, stderr) {
								console.log("gunzip err", error, stdout, stderr)
								cb(error)
							})
						} else cb(null)
					}
					
					function create_geojson(cb) {
						if( ! fs.existsSync(geojsonFile)) {
						
							var precision = Math.pow(10, 5), round = isNaN(precision)
							    ? function(x) { return x; }
							    : function(x) { return Math.round(x * precision) / precision; };

							// Convert TopoJSON back to GeoJSON.
							var topology 	= JSON.parse(fs.readFileSync(topojsonFile, "utf8"));
						    var type 		= require("topojson/lib/topojson/type");
						    var topojson 	= require("topojson");
						
							for (var key in topology.objects) {
								var object = topojson.feature(topology, topology.objects[key]);

								type({
									Feature: function(feature) {
										//if (argv["id-property"] != null) {
										//	feature.properties[argv["id-property"]] = feature.id;
										//	delete feature.id;
										//}
										return this.defaults.Feature.call(this, feature);
									},
									point: function(point) {
										point[0] = round(point[0]);
										point[1] = round(point[1]);
									}
								}).object(object);

							  fs.writeFileSync(geojsonFile, JSON.stringify(object), "utf8");
							}
						}
						
						cb(null);
					}
					
					function create_kml(cb) {
						var kmlFile = path.join(pathName, id + ".kml")
						if( ! fs.existsSync(kmlFile)) {
							var geojson	= JSON.parse(fs.readFileSync(geojsonFile, "utf8"));
							var kml 	= tokml(geojson, {
							    			name: id,
											description: 'NASA GSFC Data'
							});
							fs.writeFileSync(kmlFile, kml, "utf8");
						}
						cb(null)
					}

					function create_osm(cb) {
						var osmFile = path.join(pathName, id + ".osm")
						if( ! fs.existsSync(osmFile)) {
							console.log("create osm...")
							var geojson	= JSON.parse(fs.readFileSync(geojsonFile, "utf8"));
							console.log("tokml...")
							var osm 	= osm_geojson.geojson2osm(geojson)
							fs.writeFileSync(osmFile, osm, "utf8");	
						} 
						cb(null)
					}
					
					async.series([
						create_topojson,
						create_geojson,
						create_kml,
						create_osm
					], function(err) {
						if( !err ) {
							sendFile(res, file)
						} else {
							console.log("error", err)
							res.send("Failed to generate file:"+id+"."+fmt, 404)
						}
					})
				}
				break;
				
			case 'png':
				if( fs.existsSync(file)) {
					// this is to avoid setting the session cookie for simple images
					delete req.session;
					
					sendFile( res, file )
				} else {
					//console.log("png file does not exist", file)
					// Check on S3
					existsOnS3(region.bucket, ymd, path.basename(file), function(err) {
						if(!err) {
							sendFile( res, file )
						} else {
							res.send(404, "file not found")
						}
					})
				}
				break
		}
	},
	
	landslide_nowcast_list: function(req, res) {
		var reg_id 	= req.params.region
		var tmp_dir = app.get("tmp_dir")
		var user	= req.session.user
			
		console.log("landslide_nowcast_list", reg_id)
		switch(reg_id) {
			case 'd02':
				region = app.config.regions.d02
				break;
			case 'd03':
				region = app.config.regions.d03
				break;
			default:
				return res.send("Invalid Region", 401)
		}
		
		var dirName	= tmp_dir+"/"+region.bucket+"/*"
		var ymds 	= []

		function checkDir(dirName, cb) {
			var arr 	= dirName.split("/")
			var ymd 	= arr[arr.length-1]
			var fName	= path.join( dirName, "landslide_nowcast_"+reg_id+"_"+ymd+".topojson.gz")
			fs.exists(fName, function(exists) {
				if( exists ) {
					ymds.push(ymd)
				} 
				cb(null)
			})
		}

		glob( dirName, function (err, files) {
			if( !err && files.length > 0 ) {
				async.each(files, checkDir, function(err) {
					res.render("products/landslide_nowcast_list", {
						user: user,
						region_id: reg_id,
						ymds: ymds.sort(function(a, b){return a<b})
					})
				})
				//cb(null, files)
			} else {
				//cb(-1)				
			}
		})
	},
	
	trmm_list: function(req,res) {
		var reg_id 	= req.params.region
		var tmp_dir = app.get("tmp_dir")
		var user	= req.session.user
			
		console.log("landslide_nowcast_list", reg_id)
		switch(reg_id) {
			case 'd02':
				region = app.config.regions.d02
				break;
			case 'd03':
				region = app.config.regions.d03
				break;
			default:
				return res.send("Invalid Region", 401)
		}
		
		var dirName	= tmp_dir+"/"+region.bucket+"/*"
		var ymds 	= []

		function checkDir(dirName, cb) {
			var arr 	= dirName.split("/")
			var ymd 	= arr[arr.length-1]
			var fName	= path.join( dirName, "trmm_24_"+reg_id+"_"+ymd+".topojson.gz")
			fs.exists(fName, function(exists) {
				if( exists ) {
					ymds.push(parseInt(ymd))
				} 
				cb(null)
			})
		}

		glob( dirName, function (err, files) {
			if( !err && files.length > 0 ) {
				async.each(files, checkDir, function(err) {
					res.render("products/trmm_24_list", {
						user: user,
						region_id: reg_id,
						//ymds: ymds.sort(function(a, b){return a>b})
						ymds: ymds.sort().reverse()
					})
				})
				//cb(null, files)
			} else {
				//cb(-1)				
			}
		})
	},
	
	map: function(req,res) {
		var reg_id 		= req.params.region
		var ymd			= req.params.ymd
		var id			= req.params.id
		var host		= req.headers.host
		var date 		= moment(ymd, "YYYYMMDD")
		var user		= req.session.user
			 
		var fname		= id
		var topojson 	= req.protocol + "://" + host +"/products/" + reg_id + "/" + ymd + "/" + fname
					
		switch(reg_id) {
			case 'd02':
				region = app.config.regions.d02
				break;
			case 'd03':
				region = app.config.regions.d03
				break;
			default:
				res.send("Invalid Region", 401)
				return
		}
				
		var product = 'landslide_nowcast'
		if( id.indexOf('trmm_24') >= 0 ) {
			product = 'trmm_24'
		}
		
		var mapinfos = [
				{
					"objectType": 	"HttpActionHandler",
					"id": 			product+"_legend",
					"method": 		"GET",
					"url": 			"/mapinfo/"+product+"/legend",
					"mediaType": 	"test/html",
					"displayName": 	"legend",
				},
				{
					"objectType": 	"HttpActionHandler",
					"id": 			product+"_style",
					"method": 		"GET",
					"url": 			"/mapinfo/"+product+"/style",
					"mediaType": 	"application/json",
					"displayName": 	"style",
				},
				{
					"objectType": 	"HttpActionHandler",
					"id": 			product+"_credits",
					"method": 		"GET",
					"url": 			"/mapinfo/"+product+"/credits",
					"mediaType": 	"application/json",
					"displayName": 	"credits",
				}
			]
			
		res.render("products/map", {
			layout: 		false,
			user:  			user,
			description: 	"Product for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
			date: 			date.format("YYYY-MM-DD"),
			id: 			id,
			ymd: 			ymd, 
			region:  		region,
			worldmapid: 	app.config.worldmapid,
			fname: 			fname,
			topojson: 		topojson,
			mapinfos: 		mapinfos
		})		
	}
}
