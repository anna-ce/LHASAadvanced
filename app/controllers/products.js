var util	= require('util'),
	async	= require('async'),
	eyes	= require('eyes'),
	moment	= require('moment'),
	path	= require('path'),
	mkdirp 	= require('mkdirp'),
	filesize = require('file-size'),
	Hawk	= require('hawk'),
	debug	= require('debug')('products'),
	
	fs		= require('fs');

	var tmp_dir = __dirname + "/../../tmp"
	
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
	
	function sendPngFile( res, file ) {
		res.header("Content-Type", "image/png")
		res.header("Access-Control-Allow-Origin", "*")
		res.sendfile(path.basename(file), {root: path.dirname(file)})
	}
	
	function sendTopoJsonFile( res, file ) {
		res.header("Content-Type", "application/json")
		res.header("Content-Encoding", "gzip")
		res.header("Access-Control-Allow-Origin", "*")
		res.sendfile(path.basename(file), {root: path.dirname(file)})
	}
	
	function regionId( region ) {
		var dx = "d03"
		if( region === app.config.regions.d02 ) dx = "d02"
		return dx
	}
	
	function TRMMProductId(region, ymd) {
		return "trmm_24_"+regionId(region)+"_"+ymd
	}
	
	function findTRMMProduct(region, ymd, cb ) {
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
	
module.exports = {
	// http://localhost:7465/products/opensearch?q=daily_precipitation&lat=18&lon=-70&startTime=20140418&endTime=20140421
	
	opensearch: function(req, res) {
		var query 			= req.query.q
		var bbox			= req.query.bbox ? req.query.bbox.split(",").map(parseFloat) : undefined
		var itemsPerPage	= req.query.itemsPerPage || 7
		var startIndex		= req.query.startIndex || 1
		var startTime		= req.query.startTime ? moment(req.query.startTime, "YYYY-MM-DD") : moment()
		var endTime			= req.query.endTime ? moment(req.query.endTime, "YYYY-MM-DD") : moment()
		var lat				= req.query.lat ? parseFloat(req.query.lat) : undefined
		var lon				= req.query.lon ? parseFloat(req.query.lon) : undefined
		var user			= req.session.user
		var host			= req.protocol + "://" + req.headers.host
		var originalUrl		= host + req.originalUrl
		
		console.log("opensearch", originalUrl)
		
		if( bbox ) {
			lon = (bbox[0]+bbox[2])/2.0
			lat = (bbox[1]+bbox[3])/2.0
		}
		
		var results = []
		
		// This is the only prodcut we support
		if( query != 'daily_precipitation') return res.send(results)
		
		// find region of interest
		var region = findRegion(lat, lon)
		if( region === undefined ) return res.send( results )
			
		var ymds = []
		while( startTime.isBefore(endTime) || startTime.isSame(endTime)) {
			var ymd = startTime.format("YYYYMMDD")
			ymds.push(ymd)
			startTime.add('days', 1);
		}
		
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
							"share": 	base_url+".html"
						}
					}
					results.push(entry)
				}
				cb(null)
			}) 
		}, function(err) {
			console.log("Done OpenSearch")
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
	},
	
	index: function(req, res) {
		res.render("products/index")
	},
	
	distribute: function(req, res) {
		var reg_id 	= req.params.region
		var ymd		= req.params.ymd
		var id		= req.params.id
		var fmt		= req.params.fmt || 'html'
		
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
				res.send("Invalid Region", 401)
		}
		
		console.log("Headers", req.headers)
		console.log("Products", reg_id, ymd, id, fmt)
		
		var file 	= tmp_dir+"/"+region.bucket+"/"+ymd+"/"+id+"."+fmt
		
		switch(fmt) {
			case 'html':
				var fbAppId 	= app.config.fbAppId;
				
				if( id.indexOf('trmm_24') >= 0 ) {
					var date = moment(ymd, "YYYYMMDD")
					
					var image 		= "/products/"+reg_id+"/"+ymd+"/"+id+"_thn.png"
					var topojson 	= "/products/"+reg_id+"/"+ymd+"/"+id+".topojson.gz"
					
					res.render("products/trmm", {
						layout: 		false,
						image: 			image,
						fbAppId: 		fbAppId,
						description: 	"TRMM daily accumulated precipitation for "+region.name+" acquired on "+date.format("YYYY-MM-DD"),
						date: 			date.format("YYYY-MM-DD"),
						id: 			id,
						region:  		region,
						url: 		 	url,
						topojson: 		topojson
					})
				}
				break;
				
			case 'topojson':
				file += ".gz"
				
			case 'gz':
				if( fs.existsSync(file)) {
					sendTopoJsonFile(res, file)
				} else {
					// Check on S3
					existsOnS3(region.bucket, ymd, path.basename(file), function(err) {
						if(!err) {
							sendTopoJsonFile( res, file )
						} else {
							res.send(404, "file not found")
						}
					})
				}
				break
				
			case 'png':
				if( fs.existsSync(file)) {
					sendPngFile( res, file )
				} else {
					// Check on S3
					existsOnS3(region.bucket, ymd, path.basename(file), function(err) {
						if(!err) {
							sendPngFile( res, file )
						} else {
							res.send(404, "file not found")
						}
					})
				}
				break
		}
	}
}
