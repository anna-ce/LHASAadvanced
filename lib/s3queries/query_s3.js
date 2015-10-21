var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	_			= require('underscore'),
	mime		= require('mime-types'),
	Hawk		= require('hawk'),
	filesize 	= require('filesize'),
	mkdirp		= require("mkdirp"),
	request		= require('request'),
	geopix		= require('geopix'),
	topojson	= require('topojson'),
	topotype 	= require("topojson/lib/topojson/type"),
	zlib 		= require('zlib'),
	debug		= require('debug')('s3'),
	turf		= require('turf'),
	Terraformer = require('terraformer'),
	TArcGIS 	= require('terraformer-arcgis-parser'),
	lockFile 	= require('lockfile'),
	mkdirp		= require('mkdirp'),
	osm_geojson	= require('osm-and-geojson'),

	GeoStore 		= require('terraformer-geostore').GeoStore,
	RTree 			= require('terraformer-rtree').RTree,
	//LevelStore 	= require('terraformer-geostore-leveldb'),
	LocalStorage 	= require('terraformer-geostore-localstorage').LocalStorage,
	MemoryStorage 	= require('terraformer-geostore-memory').Memory,

	exec		= require('child_process').exec
	;
	
	Terraformer.ArcGIS	= TArcGIS;
	
	//var levelstore = new LevelStore()
	
	//	
	// Converts topojson to geojson
	//
	function ConvertToGeoJSON( fileName, cb ) {
		try {
		var gzip 		= zlib.createGunzip();
		var inp 		= fs.createReadStream(fileName);
		var data		= ''
		inp.pipe(gzip)
			.on('data', function(chunk) { data += chunk })
			.on('end', function() {
			
				var topology = JSON.parse(data)

				var precision = Math.pow(10, 5), round = isNaN(precision)
			    ? function(x) { return x; }
			    : function(x) { return Math.round(x * precision) / precision; };

				// convert to geojson					
				for (var key in topology.objects) {
					var geojson = topojson.feature(topology, topology.objects[key]);
					topotype({
						Feature: function(feature) {
							return this.defaults.Feature.call(this, feature);
						},
						point: function(point) {
							point[0] = round(point[0]);
							point[1] = round(point[1]);
						}
					}).object(geojson);
				}
				cb(null,geojson)
			})
		} catch(e) {
			logger.error("ConvertToGeoJSON err", e)
			cb(500)
		}
	}
	
	function DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, geojsonfileName, bucket, subfolder, year, doy, newprefix, cb) {
		console.log("DownloadTopojsonFilefromS3andConvertToGeoJSON", newprefix, geojsonfileName)

		var geojsonLockFile 	= geojsonfileName + ".lock"


		function GetGeoJSON(err, geojson) {
			if( !err ) {
				fs.writeFileSync(geojsonfileName, JSON.stringify(geojson))
				lockFile.unlockSync(geojsonLockFile)
				console.log("unlocked", geojsonLockFile)
				cb(null, geojson)					
			} else {
				lockFile.unlockSync(geojsonLockFile)
				console.log("unlocked", geojsonLockFile)
				cb(err)
			}
		}

		var options = {
			wait: 		1000,
			retries: 	10
		}
		
		lockFile.lock(geojsonLockFile,options, function(err) {
			if( err ) return cb(err)
			console.log("Locking", geojsonLockFile )
			if(!fs.existsSync(topofileName)) {				
				DownloadFilefromS3(bucket, subfolder, year, doy, newprefix, function(err) {
					if( !err ) {
						console.log("No Error getting from S3")
						ConvertToGeoJSON( topofileName, GetGeoJSON )
					} else {
						logger.error("DownloadTopojsonFilefromS3andConvertToGeoJSON Error getting from S3", err)
						lockFile.unlockSync(geojsonLockFile)
						console.log("unlocked", geojsonLockFile)
						cb(err)
					}
				})
			} else {
				if( !fs.existsSync(geojsonfileName)) {
					console.log("topojson.gz exists... decompress it...")
					ConvertToGeoJSON( topofileName, GetGeoJSON )
				} else {
					console.log("geojson exists...read it")
					var geojson = fs.readFileSync(geojsonfileName, "utf8")
					lockFile.unlockSync(geojsonLockFile)
					console.log("unlocked", geojsonLockFile)
					cb(null, JSON.parse(geojson))
				}
			}
		})
	}
	
	function makePoly( bbox, options ) {
		var feature = turf.polygon([[
			[ bbox[0], bbox[1] ],
			[ bbox[0], bbox[3] ],
			[ bbox[2], bbox[3] ],
			[ bbox[2], bbox[1] ],
			[ bbox[0], bbox[1] ]
		]], options)
		
		return feature
	}
	
	function getGeopixValue(fileName, lat, lng) {
		
		var tif		= geopix.GEOTIFFFile(fileName)
		var value 	= tif.LatLng(lat, lng)
		console.log("getGeopixValue", fileName, lat, lng, value)
		return value
	}
	
	function GetUserLocation(req, cb) {
			
		var ip = (req.headers['x-forwarded-for'] || '').split(',')[0] || req.connection.remoteAddress
		if(ip.indexOf("::")>=0 ) return cb(null, 38.0, -76.0)

		var url = 'http://freegeoip.net/json/' + ip
		console.log("GetUserLocation", url)
		request.get( url, function (error, response, body) {
			if(!error && response.statusCode == 200 ) {
				var data = JSON.parse(body)
				console.log(data)
				cb(error, data.latitude, data.longitude)
			} else {
				//("Error", error, ip)
				cb(error, undefined, undefined)
			}
		})
	}
	
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
	
	var Query = function( options ) {
		this.options 		= options
		this.bucketList 	= {}
	}
		
	// Find Region that would match that Lat/Lon
	Query.prototype.FindRegionKey = function(lat, lon) {
		var regions = app.config.regions
		for( var r in regions ) {
			var region = regions[r]
			if( r != "Global") {
				if( InBBOX(lat, lon, region.bbox)) {
					return r
				}
			}
		}
		return undefined
	}
	

	//
	// List all objects in bucket/subfolder
	//
	Query.prototype.ListObjects = function( bucket, prefix, next) {
		var slf = this
		//console.log("ListObjects", prefix)
		
		// Get a list of all objects in that bucket's subfolder (WARNING: limit=1000)
		var params = {
			Bucket: bucket || slf.options.bucket,
			Prefix: slf.options.subfolder
		};
		
		//console.log("params", params)
		app.s3.listObjects(params, function(err, data) {
			if (err) {
				logger.error(err, err.stack); 	// an error occurred
				next(err)
			} else {
				//console.log(data);				// successful response
			
				slf.bucketList = {}
				
				var contents 	= data.Contents
				_.each(data.Contents, function(elt) {
					var size 	= elt.Size
					var arr		= elt.Key.split("/")
					var name	= _.last(arr)
					var key		= elt.Key.replace(name, "")
					
					
					//console.log(prefix, name, key, elt.Key)		
					if( prefix && (name.indexOf(prefix) >= 0)) {
						if( slf.bucketList[key] != undefined ) {
							slf.bucketList[key].push( { key: name, size: size } )
						} else {
							slf.bucketList[key] = [ { key: name, size: size } ]
							//console.log("added to key", key, name)
						}
					} else {
						// if( prefix ) console.log("not added to key", prefix, key, name)
					}
				})
				//console.log( JSON.stringify(slf.bucketList))
				next(null)
			}    
		});
	}
	
	//
	// Check if we have current list of object in bucket
	// if not, get it
	//
	Query.prototype.landslide_catalog = function(bucket, prefix, next) {
		if( _.isEmpty(this.bucketList)) {
			//console.log("Fill Empty Bucket...", prefix)
			this.ListObjects(bucket, prefix, next)
		} else {
			next()
		}
	}
	
	Query.prototype.QueryByID = function(req, user, year, doy, regionKey, prefix, credentials, cb ) {
		var date			= moment(year+"-"+doy)
		var duration		= 60 * 30
		//var id			= this.options.subfolder + "_" + year.toString() + doy
		var id				= prefix + "_" + year.toString() + doy
		var host 			= req.protocol + "://"+ req.get('Host')
		var bucket			= app.config.regions[regionKey].bucket
		
		function Bewit(url) {
			if( credentials ) {
				var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
				url += "?bewit="+bewit
			} 
			return url;
		}
		
		var jday	= date.dayOfYear()
		if( jday < 10 ) {
			jday = "00"+jday
		} else if( jday < 100 ) jday = "0"+jday
		
		var month 	= date.month() + 1
		if( month < 10 ) month = "0"+ month

		var day		= date.date();
		if( day < 10 ) day = "0"+day
			
		var key 	=  this.options.subfolder + "/" + date.year() + "/" + doy + "/"
		
		var entry 	= undefined
		var self	= this
			
		function checkIfProductInBucketList(next) {
			self.CheckIfProductInBucketList(req, key, year, month, day, jday, id, Bewit, regionKey, prefix, function(err, data) {
				entry = data
				next(err)
			})
		}
		
		function checkEmptyBucket(next) {
			self.landslide_catalog(bucket, prefix, next)
		}
		
		async.series([ 
			checkEmptyBucket,
			checkIfProductInBucketList
		], function(err) {
			return cb(err, entry)
		})
	}
	
	Query.prototype.CheckRequestedDay = function( req, user, d, startTime, endTime, prefix, credentials, regionKey, entries, cb  ) {
		var time			= endTime.clone()
		time	 			= time.subtract(d, "days");
	
		var year 			= time.year();
		var doy  			= padDoy(time.dayOfYear());
			
		this.QueryByID(req, user, year, doy, regionKey, prefix, credentials, function(err, entry) {
			if( entry ) entries.push(entry)
			cb(null)
		})
	}

	Query.prototype.CheckIfProductInBucketList = function(req, key, year, month, day, jday, id, Bewit, regionKey, prefix, next) {
		if( this.bucketList[key] != undefined ) {				
			var artifacts			= this.bucketList[key]
			var host 				= req.protocol + "://"+ req.get('Host')
			var date				= moment(year+"-"+jday)
			var bucket				= app.config.regions[regionKey].bucket
			
			var s3host				= "https://s3.amazonaws.com/"+bucket +"/"+ this.options.subfolder+"/"+year+"/"+jday + "/"
			
			var thn_ext				= this.options.browse_img  || "_thn.jpg"
			
			var browse_img			= _.find(artifacts, function(el) { 
											return (el.key.indexOf(thn_ext) > 0) || (el.key.indexOf("_thn.jpg") > 0)
										}).key 
			
			var downloads = []
			
			// local host cache for S3
			var s3proxy				= host+'/products/s3/'+regionKey+"/"+ this.options.subfolder+"/"+year+"/"+jday + "/"
			
			function checkFilePresent( subfolder, ftype, mediaType, format, fmt ) {
				if(ftype) {
					var fkey, size;
					
					try {						
						var obj  =  _.find(artifacts, function(el) { 
							return (el.key.indexOf(fmt) > 0) && (el.key.indexOf(fmt+".") < 0) 
						})

                        if( obj == undefined ) {
							logger.debug(fmt, "not found in ", artifacts)
							return
						}

						fkey = obj.key
						size = obj.size
						//console.log("checkFilePresent", fkey, size)
						
						var download_file = {
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"mediaType": 	mediaType,
							"url": 			Bewit(s3proxy+ fkey),
							"size": 		filesize( size, {round:2, suffixes: {
												"B": req.gettext("filesize.B"), 
												"kB": req.gettext("filesize.KB"), 
												"MB": req.gettext("filesize.MB"), 
												"GB": req.gettext("filesize.GB"), 
												"TB": req.gettext("filesize.TB")}}),
							"displayName": 	req.gettext(format)
						}
						downloads.push(download_file)
					} catch(e) {
						logger.error("could not find size of file", fkey, e)
					}
				}
			}
			
			checkFilePresent( this.options.subfolder, this.options.geojson, 	"application/json", 	"formats.geojson", 		".geojson" )
			checkFilePresent( this.options.subfolder, this.options.geojsongz, 	"application/gzip", 	"formats.geojsongz", 	".geojson.gz" )
			checkFilePresent( this.options.subfolder, this.options.topojson_gz, "application/gzip", 	"formats.topojsongz", 	".topojson.gz" )
			checkFilePresent( this.options.subfolder, this.options.topojson, 	"application/json",		"formats.topojson", 	".topojson" )
			checkFilePresent( this.options.subfolder, this.options.shape_gz, 	"application/gzip", 	"formats.shpgz", 		".shp.gz" )
			checkFilePresent( this.options.subfolder, this.options.shape_zip, 	"application/zip", 		"formats.shpzip", 		".shp.zip" )
			checkFilePresent( this.options.subfolder, this.options.geotiff, 	"application/tiff", 	"formats.geotiff", 		".tif" )
		
			actions = [
				{ 
					"@type": 			"ojo:browse",
					"displayName": 		req.gettext("actions.browse"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/browse/"+regionKey+"/"+year+"/"+jday+"/"+prefix),
						"mediaType": 	"html"
					}]
				},
				{
					"@type": 			"ojo:download",
					"displayName": 		req.gettext("actions.download"),
					"using": 			downloads
					
				},
				{
					"@type": 			"ojo:map",
					"displayName": 		req.gettext("actions.map"),
					"using": [
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"legend",
							"url": 			host+"/mapinfo/"+this.options.subfolder+"/legend",
							"mediaType": 	"text/html",
							"displayName": 	req.gettext("mapinfo.legend")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"style",
							"url": 			host+"/mapinfo/"+this.options.subfolder+"/style",
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("mapinfo.style")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"credits",
							"url": 			host+"/mapinfo/"+this.options.subfolder+"/credits",
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("mapinfo.credits")
						}
					]
				}
			]
		
			if( this.options.getvalue ) {
				var getvalueAction = {
					"@type": 			"ojo:value",
					"displayName": 		req.gettext("actions.value"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/value/"+regionKey+"/"+year+"/"+jday+"/"+prefix+"?latitude={latitude}&longitude={longitude}"),
						"mediaType": 	"application/json"
					}]
				}
				actions.push(getvalueAction)
			}

			if( this.options.subset_action ) {
				var getvalueAction = {
					"@type": 			"ojo:subset",
					"displayName": 		req.gettext("actions.subset"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/subset/"+regionKey+"/"+year+"/"+jday+"/"+prefix+"."+date.format("YYYYMMDD")+"?bbox={LLlon},{LLlat},{URLon},{URLat}"),
						"mediaType": 	"application/vnd.geo+json"
					}]
				}
				actions.push(getvalueAction)
			}

			
			if( this.options.metadata ) {
				var metadata = {
					"@type": 			"ojo:metadata",
					"displayName": 		req.gettext("actions.metadata"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/metadata/"+regionKey+"/"+year+"/"+jday+"/"+prefix),
						"mediaType": 	"application/json"
					}]
				}
				actions.push(metadata)
			}
			
			if( this.options.exports ) {
				var exports = {
					"@type": 			"ojo:export",
					"displayName": 		req.gettext("actions.export"),
					"using": 			[]
				}

				for( var e in this.options.exports ) {
					var exp = this.options.exports[e]
					//console.log("Adding", host+"/products/"+ this.options.subfolder+"/export/"+regionKey+"/"+year+"/"+jday+"/"+prefix+"."+date.format("YYYYMMDD")+"."+exp.ext)
					var u = {
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/export/"+regionKey+"/"+year+"/"+jday+"/"+prefix+"."+date.format("YYYYMMDD")+"."+exp.ext),
						"displayName": 	exp.ext,
						"mediaType": 	exp.mediaType
					}
					exports.using.push(u)
				}
				actions.push(exports)
			}
			
			if( this.options.esri ) {
				var exports = {
					"@type": 			"ojo:esri",
					"displayName": 		req.gettext("actions.esri"),
					"using": 			[{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/features/"+regionKey+"/"+year+"/"+jday+"/"+prefix+"."+date.format("YYYYMMDD")+".geojson"),
						"mediaType": 	"application/json"
					}]
				}
				actions.push(exports)
			}
			
			var source 		= req.gettext(this.options.source)
			var sensor 		= req.gettext(this.options.sensor)
			var url 		= this.options.original_url

			var properties = {
				"source": {
					"@label": req.gettext("properties.source"),
					"@value": source
				},
				"url": {
					"@label": req.gettext("properties.url"),
					"@value": url
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
					"@value": this.options.resolution
				}
			}
			var bbox = app.config.regions[regionKey].bbox
			var entry = {
				"@id": 			id,
				"@type": 		"geoss:"+this.options.product,
				"displayName": 	(this.options.displayName || prefix)+" "+year+"/"+month+"/"+day,
				"image": 		[ 
									{
										"url": s3proxy+browse_img,
										"mediaType": "image/png",
										"rel": "browse"
									}
								],
				"properties": 		properties,
				"geometry": {
					"type": "Polygon",
					"coordinates": [[
						[bbox[0], bbox[1]],
						[bbox[0], bbox[3]],
						[bbox[2], bbox[3]],
						[bbox[2], bbox[1]],
						[bbox[0], bbox[1]]
					]]
				},
				"action": 			actions
			}
			//console.log("CheckIfProductInBucketList", JSON.stringify(entry))
			next(null, entry)
		} else {
			//console.log("CheckIfProductInBucketList not found", key, this.bucketList)
			next(null, null)
		}
	}
	
	Query.prototype.QueryAll = function(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
		var product 	= this.options.product
		var subfolder	= this.options.subfolder
		var tags	 	= this.options.tags
		 
		logger.debug("QueryAll", query)
		
		if( tags.indexOf(query) < 0 ) {
			console.log("unsupported S3 query", query, tags)
			return cb(null, null)
		}
	
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
	
		// override default bucket based on location
		var regionKey  	= this.FindRegionKey(lat, lon)
		if(regionKey == undefined )	{
			logger.error("Undefined RegionKey", lat, lon)
			return cb(null, null)
		}
			
		var bucket		= app.config.regions[regionKey].bucket
		
		if( bucket ) {
			logger.debug("Found bucket", bucket)
		} else {
			logger.error("Cannot find bucket for", lat, lon)
			return cb(null, null)
		}
			
		if( bbox ) {
			lon = (bbox[0]+bbox[2])/2
			lat = (bbox[1]+bbox[3])/2
		}
	
		var days = []
		
		maxLimit = 90
		if (limit > maxLimit) maxLimit = limit
		itemsPerPage = maxLimit;
		for( var i=0; i<itemsPerPage; i++ ) {
			days.push(i)
		}
	
		var entries	= []
		
		//
		// Check every requested day
		//
		var slf 	= this
		var prefix 	= product;
		if( slf.options.prefix_map ) prefix = slf.options.prefix_map[query]

		function checkAllRequestedDays(next) {
			async.each(days, function(d, cb2) {
				if( entries.length < limit ) {
					slf.CheckRequestedDay( req, user, d, startTime, endTime, prefix, credentials, regionKey, entries, cb2) 
				} else {
					cb2(null)
				} 
			}, function(err) {
				next(null)				
			})
		}
		
		function getNewBucketList(next) {
			slf.ListObjects( bucket, prefix, function(err) {
				next(null)
			})
		}
		
		if( (slf.options.bucket === undefined) &&  slf.options.entry ) {
			var json = {
				replies: {
					items: [slf.options.entry(req)]
				}
			}
	
			return cb(null, json)
		}
		
		async.series([
			getNewBucketList, 
			checkAllRequestedDays
		], function(err) {
			var json = {}
			
			if( !err ) {
				json.replies = {
					items: entries
				}
			}
			//console.log(product, " got entries:", entries.length)
			cb(err, json)			
		})
	}
	
	function render_map(region, url, prefix, description, req, res) {
		console.log("render_map", url)
		var latitude, longitude;
		
		if( region.name == 'Global') {
			return GetUserLocation(req, function(err, lat, lon) {
				//region.bbox = undefined
				res.render("products/map_api", {
					region: 	region,
					url: 		url,
					layout: 	false,
					latitude: 	lat,
					longitude: 	lon,
					description: description,
					zoom: 3
				})
			})
		} else {
			latitude 	= region.target[1]
			longitude 	= region.target[0]
		
			res.render("products/map_api", {
				region: 	region,
				url: 		url,
				layout: 	false,
				latitude: 	latitude,
				longitude: 	longitude,
				description: description,
				zoom: 6
			})
		}
	}
	
	Query.prototype.Process = function(req,res) {
	}

	// Retrieve value for particular lat/lng
	Query.prototype.Value = function(req, res) {
		var subfolder	= req.params['subfolder']
		var regionKey	= req.params['regionKey']
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prod		= req.params['prefix']
		var region		= app.config.regions[regionKey]
		
		var user		= req.session.user
		var credentials	= req.session.credentials
		
		// let's find the actual product name 
		// var source 		= productQueries[subfolder]
		var options 	= this.options.prefix_map
		
		var latitude	= parseFloat(req.query['latitude'])
		var longitude	= parseFloat(req.query['longitude'])
		var dt			= moment(year+"/"+doy, "YYYY/DDD")
		
		logger.debug("Get Value", subfolder, regionKey, year, doy, prod, options, latitude, longitude)
		
		
		if( latitude == undefined ) 				return res.send('404', 'Undefined Latitude')
		if( latitude > 90 || latitude < -90 ) 		return res.send('404', 'Invalid Latitude')
		if( longitude == undefined ) 				return res.send('404', 'Undefined longitude')
		if( longitude > 180 || longitude < -180 ) 	return res.send('404', 'Invalid longitude')
			
		var tmp_dir 	= app.get("tmp_dir")
		var bucket		= this.options.bucket
		var subfolder	= this.options.subfolder
		var id			= prod+"."+dt.format("YYYYMMDD")
			
		var fileName	= path.join(tmp_dir, bucket, subfolder, year, doy, id+".tif")
			
		var json 	= {
			'id': 		id,
			'lat': 		latitude,
			'lng': 		longitude,
			"name": 	this.options.product,
			'value': 	"??"
		}
		
		try {
			if( !fs.existsSync(fileName)) {
				var options = {
					Bucket: bucket, 
					Key:  subfolder+"/"+year+"/"+doy+"/"+id+".tif"
				};
				var getval = this.options.getvalue
				app.s3.headObject(options, function(err, data) {
					if (err) {
						logger.debug("headObject", options, "error", err, err.stack); // an error occurred
						return res.sendStatus(500)
					} else {
						logger.debug("Object seems to be there...creating", fileName)
						var file = fs.createWriteStream(fileName);
						app.s3.getObject(options)
						.createReadStream()
						.pipe(file)
			
						file.on('close', function() {
							logger.debug("got file from S3", fileName)
							var result 	= getGeopixValue(fileName, latitude, longitude)
							json.value 	= getval(result)
							res.send(json)
						});
					}    
				});
			} else {
				logger.debug("File exists... getting geopix...")
				var result 	= getGeopixValue(fileName, latitude, longitude)
				json.value 	= this.options.getvalue(result)
				
				res.send(json)
			}
		} catch(e) {
			logger.error("Error", e)
			res.send(json)			
		}
	}
	
	Query.prototype.QueryProduct = function(req, res) {
		var subfolder	= req.params['subfolder']
		var regionKey	= req.params['regionKey']
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prod		= req.params['prefix']
		
		var user		= req.session.user
		var credentials	= req.session.credentials
		
		// let's find the actual product name 
		// var source 		= productQueries[subfolder]
		var options 	= this.options.prefix_map
		
		// find the key
		//var prefix		= _.invert(options)[prod]

		//console.log('QueryProduct', regionKey, year,doy, prod, subfolder, options, prefix)
		if( this.options.bucket == undefined ) {
			var geojson = this.options.entry(req)
			return res.send(geojson)
		}
		this.QueryByID(req, user, year, doy, regionKey, prod, credentials, function( err, entry ) {
			if( !err ) {
				//console.log("QueryByID:", entry)
				res.json(entry)
			} else {
				//console.log("no entry")
				res.sendStatus(500)
			}				
		})
	}
	
	Query.prototype.Map = function(req,res) {
		var subfolder	= req.params['subfolder']
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var prefix		= req.params['prefix']
		var bucket		= region.bucket

		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var date;
		if( year != "-") {
			date 		= moment(year+"-"+doy)
		} else {
			date 		= moment()
		}
		
		var host 		= req.protocol + "://"+ req.get('Host')
		var bbox		= bbox
		var id			= this.options.subfolder+year+"-"+doy
		
		var legend				= "legend."+ this.options.product+".title"
		var product_title 		= this.options.product
		var product_description	= req.gettext(legend)
		//console.log(legend, product_description)
		
		if( this.options.prefix_map ) {
			var str = "legend."+product_title+"."+prefix
			product_description	= req.gettext(str)
		}
		product_description += " - " + date.format("YYYY-MM-DD")
		var url = host + "/products/" + this.options.subfolder + "/query/"+regionKey+"/"+year+"/"+doy+"/"+prefix
		render_map(region, url, prefix, product_description, req, res )
	}
	
	function sendFile( res, file ) {
		var ext 		= path.extname(file)
		var basename 	= path.basename(file)
		var dirname 	= path.dirname(file)
		var ext			= path.extname(file)
		
		var mime_type = mime.lookup(path.basename(file))
		//console.log("sendFile", file, ext, mime_type)
		
		if( (basename.indexOf(".topojson.gz") > 0) || (basename.indexOf(".geojson.gz") > 0) ) {
			res.header("Content-Type", "application/json")
			res.header("Content-Encoding", "gzip")
			//console.log("sending .topojson application/json gzip", basename)
		} else {
			//console.log("sending ", mime_type, basename, dirname)
			res.header("Content-Type", mime_type, basename)
			debug(ext, mime_type, "no encoding")
		}
		res.header("Access-Control-Allow-Origin", "*")
		res.sendFile(basename, {root: dirname})
	}
	
	function DownloadFilefromS3(bucket, subfolder, year, doy, id, cb ) {
		//console.log("DownloadFilefromS3", bucket, subfolder, year, doy, id)

		var s3host		= "http://s3.amazonaws.com/"
		var s3fileName	= s3host + bucket+"/"+subfolder+"/" + year + "/" + doy + "/" + id

		//console.log("DownloadFilefromS3 s3fileName", s3fileName)

		var tmp_dir 	= app.get("tmp_dir")
		var fileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, id)
		if( fs.existsSync(fileName)) {
			return cb(null)
		}
		
		// Not there... will have to download
		var dirName	 	= path.dirname(fileName)				
		// Make sure we have a directory for it
		if( !fs.existsSync(dirName)) mkdirp.sync(dirName)
		var options = {
			Bucket: bucket, 
			Key: subfolder +"/"+year+"/"+doy+"/"+id
		};
		
		try {
			app.s3.headObject(options, function(err, data) {
				if (err) {
					console.log("headObject options", options)
					logger.error("headObject", err, err.stack); // an error occurred
					return cb(500)
				} else {
					console.log("Downloading from S3...", fileName)
					var file = fs.createWriteStream(fileName);
			
					file.on('close', function() {
						//console.log("Closing", fileName)
						file.end()
						//var stats = fs.statSync(fileName)
						//console.log(stats)
						cb(null)
					});
			
					app.s3.getObject(options)
					.createReadStream()
					.pipe(file)
				}    
			});
		} catch(e) {
			logger.error("error getting from S3", options, e)
			return cb(500)
		}
	}
	
	//
	// Get the file from S3 and forwards it back with gzip header for unzipping
	// We could also cache it for speed
	//
	Query.prototype.S3 = function(req,res) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket

		var subfolder	= req.params['subfolder']
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var id			= req.params['id']
	
		var tmp_dir 	= app.get("tmp_dir")
		var filedir		= path.join(tmp_dir, bucket, subfolder, year, doy)
		if( !fs.existsSync(filedir)) {
			 mkdirp.sync(filedir)
		}
		var fileName 	= path.join(filedir, id)
		//console.log(fileName)
		
		if( (this.options.bucket == undefined) &&  this.options.GetGeoJSON) {
			this.options.GetGeoJSON( function(err, geojson) {
				fs.writeFileSync(fileName, JSON.stringify(geojson))
				if(!err) {
					sendFile(res,fileName)
				} else {
					res.sendStatus(err)
				}
			})
		} else {
			DownloadFilefromS3(bucket, subfolder, year, doy, id, function(err) {
				if(!err) {
					sendFile(res, fileName)
				} else {
					res.sendStatus(err)
				}
			})
		}
	}

	// Lon, lat format
	function ValidBBOX(bbox) {
		var arr = _.map(bbox.split(","), function(s) { return parseFloat(s) })

		console.log(arr)

		if(isNaN(arr[0]) || isNaN(arr[1]) || isNaN(arr[2]) || isNaN(arr[3]) ) return false
			
		if ( (arr[1] < -90) || (arr[1] > 90)) return false
		if ( (arr[3] < -90) || (arr[3] > 90)) return false
		if ( (arr[0] < -180) || (arr[0] > 180)) return false
		if ( (arr[2] < -180) || (arr[2] > 180)) return false
		
		return true	
	}
	
	Query.prototype.Subset= function(req,res) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket
		var subfolder	= req.params['subfolder']
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prefix 		= req.params['prefix']

		var tmp_dir 	= app.get("tmp_dir")
		var fileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, prefix+".geojson")
		var bbox		= req.query['bbox']
		console.log("Subset bbox", bbox)
		
		if( !bbox || !ValidBBOX(bbox))	{
			logger.error("Invalid bbox for subsetting", bbox)
			return res.sendStatus(406, "Invalid BBOX")
		}

		bbox 			= _.map(bbox.split(","), function(s) { return parseFloat(s) })
		
		console.log("Subset", bbox)
		
		function subsetGeojson( bbox, geojson, res ) {
			var poly1 = makePoly(bbox, null)
			var features = [];
			for (var f in geojson.features ) {
				try {
					var intersection = turf.intersect(poly1, geojson.features[f])
					if( intersection ) {
						intersection.properties = geojson.features[f].properties
						features.push(intersection)
					} 
				} catch(e) {
					logger.error("turf intersect error", e);
					logger.error("subsetGeojson dies in feature", f)
					//return res.sendStatus(500)
				}
			}
			logger.info("subset done... #features:", features.length)
			geojson.features = features
			
			res.json(geojson)
		}
		
		if( !fs.existsSync(fileName)) {
			var newprefix 		= prefix + ".topojson.gz"
			var topofileName 	= fileName.replace(".geojson", ".topojson.gz")
			
			console.log("Trying DownloadTopojsonFilefromS3andConvertToGeoJSON...", newprefix, topofileName)
			DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, fileName, bucket, subfolder, year, doy, newprefix, function(err, geojson) {
				subsetGeojson( bbox, geojson, res)
			})
		} else {
			console.log("geojson file exists... read and subset it...")
			var geojson = fs.readFileSync(fileName, "utf8")
			subsetGeojson( bbox, JSON.parse(geojson), res )
		}
	}
	
	var geoStoreCache = {}
	
	// we need to go through older entries and remove them
	function CleanStore() {
		var now = moment()
		for( var s in geoStoreCache ) {
			if( geoStoreCache[s]) {
				var store 	= geoStoreCache[s]
				var dt		= geoStoreCache[s].created_at
				var diff	= now.diff(dt)
				var dur		= moment.duration(diff).days()
				if( dur > 1 ) {
					// delete that old store
					logger.info("deleting store", s, " created at", dt.format("YYYY-MM-dd"))
					delete geoStoreCache[s]
				}
			}
		}
	}

	Query.prototype.FeatureService= function(req,res) {
		var user		= req.session.user
		var host 		= req.protocol + "://"+ req.get('Host')
		var prefix		= req.params['prefix'].split(".")[0]
		
		if( prefix.indexOf("gpm_") >= 0) {
			prefix = prefix.replace("gpm_", "precip_")
		} else if( prefix === "flood_14km") prefix = "flood_nowcast"
			
		res.render("esri/featureservice.ejs", {
			user: 		user,
			host: 		host,
			prefix: 	prefix,
			example: 	host+"/esri/"+prefix
		})			
	}
	
	Query.prototype.Features= function(req,res) {
		var regionKey			= req.params['regionKey']
		var region				= app.config.regions[regionKey]
		var bucket				= region.bucket
		var subfolder			= req.params['subfolder']
		var year 				= req.params['year']
		var doy 				= req.params['doy']
		var prefix 				= req.params['prefix']
		var tmp_dir 			= app.get("tmp_dir")
		var fileName 			= path.join(tmp_dir, bucket, subfolder, year, doy, prefix)
			
		var where				= req.query['where']
		var geometry			= JSON.parse(req.query['geometry'])
		var geometryPrecision	= req.query['geometryPrecision']
		var maxAllowableOffset	= req.query['maxAllowableOffset']
		var fmt					= req.query['f']
		
		var bbox 		= new Terraformer.Polygon({
  		  "type": "Polygon",
 		   "coordinates": [
			   [ [geometry.xmin, geometry.ymin], [geometry.xmin, geometry.ymax], [geometry.xmax, geometry.ymax], [geometry.xmax, geometry.ymin], [geometry.xmin, geometry.ymin] ]
   			]
	 	});

		var attributes	= this.options.attributes
		
		//console.log("geometry", JSON.stringify(geometry))
		//console.log("bbox", JSON.stringify(bbox))
		//console.log("Features", prefix )
		
		//
		// Check features within GeoStore based on provided bbox
		// and send them back as a FeatureServer Collection
		//
		var slf = this
		
		function CheckStore( store ) {
			var featureCollection = { 	
				"type": "FeatureCollection",
				"geometryType": "esriGeometryPolygon",
				"globalIdFieldName": "",
				"objectIdFieldName": "objectid",
				"spatialReference": {
					"latestWkid": 4326,
					"wkid": 4326
		   		},
				"features": [],
				"fields": [
					{
					   "alias": "OBJECTID",
					   "name": "objectid",
					   "type": "esriFieldTypeOID"
					}
				]
			};
			
			if( attributes) {
				_.each(attributes, function(att) {
					featureCollection.fields.push(att)
				})
			}
			
			store.within(bbox, function(err, features) {
				//console.log("within", err, features.length)
				for( var f in features) {
					var feature = features[f]
					var feat = {
						attributes: feature.properties
					}
					
					if( feature.geometry.type === "Polygon") {
						feat.geometry = {
							rings: feature.geometry.coordinates
						}
					} else if( feature.geometry.type === "Point") {
						feat.geometry = {
							x: feature.geometry.coordinates[0],
							y: feature.geometry.coordinates[1]
						}
					} else {
						console.log("Unknow feature type", feature.geometry.type)
					}
					
					feat.attributes.objectid = feature.id
					featureCollection.features.push(feat)						
				}
				res.send(featureCollection)
				CleanStore()
			})
		}
		
		//
		// If GeoStore does not exist, we need to create it
		//
		function CreateStore(callback) {
			
			function CreateStoreFromGeoJSON(geojson, cb) {
				var id 			= 1
				//var levelstore 	= new LevelStore()
			    var memstore 	= new MemoryStorage();

				var store 		= new GeoStore({
					store: memstore,
					index: new RTree()
				});

				if( geojson && geojson.features && geojson.features.length>0) {
					async.each(geojson.features, function(f, next) {
						f.id = id
						store.add(f, function(err, res) {
							next(err)
							id += 1
						})
					}, function(err) {
						//console.log("Store created for", prefix)
						geoStoreCache[prefix] = {
							created_at: moment(),
							store: store
						}
						cb(err, store)
					})
				} else {
					if( !geojson ) {
						logger.error("geojson undefined")
					} else if( !geojson.features) {
						logger.error("geojson features undefined")						
					} else if( !geojson.features.length <=0 ) {
						logger.error("geojson features length", geojson.features.length )						
					}
					logger.error("Failed CreateStore")
					cb(500, null)
				}
			}

			if( !fs.existsSync(fileName)) {
				if( (slf.options.bucket === undefined) &&  slf.options.GetGeoJSON ) {
					slf.options.GetGeoJSON( function(err, geojson) {
						if( !err ) {
							CreateStoreFromGeoJSON(geojson, callback)
						} else {
							logger.info("GetGeoJSON Error", err)
						}
					})
				} else {
					var newprefix 		= prefix.replace("geojson","topojson.gz")
					var topofileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)			
		
					if( slf.options.bucket != undefined) bucket = self.options.bucket
		
					DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, fileName, bucket, subfolder, year, doy, newprefix, function(err, geojson) {
						CreateStoreFromGeoJSON(geojson, callback)
					})					
				}
			} else {
				var geojson 	= JSON.parse(fs.readFileSync(fileName, "utf8"))
				CreateStoreFromGeoJSON(geojson, callback)
			}
		} // End of CreateStore
		
		var cacheDir			=  path.join(tmp_dir, bucket, subfolder, year, doy)
		if( !fs.existsSync(cacheDir)) {
			mkdirp.sync(cacheDir)	
		}
		var geoStoreCacheLock 	= path.join(tmp_dir, bucket, subfolder, year, doy, prefix+".geocache.lock")
		
		//console.log("geoStoreCacheLock", geoStoreCacheLock)
		var options = {
			wait: 		1000,
			retries: 	100
		}
		
		lockFile.lock(geoStoreCacheLock, options, function(err) {	
			if( err ) console.log("Lock err", err)
			if( geoStoreCache[prefix] === undefined ) {
				//console.log("geoStore does not exist", prefix)
				CreateStore(function(err, store) {
					if( !err ) CheckStore(store)
					lockFile.unlockSync(geoStoreCacheLock)
					//console.log("geoStore unlocked")
						
				})
			} else {
				//console.log("geoStore exists", prefix)
				CheckStore(geoStoreCache[prefix].store)
				lockFile.unlockSync(geoStoreCacheLock)
				//console.log("geoStore unlocked")
			}	
		})
	}
	
	Query.prototype.Export= function(req,res) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket
		var subfolder	= req.params['subfolder']
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prefix 		= req.params['prefix']
		
		var tmp_dir 	= app.get("tmp_dir")
		var fileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, prefix)
				
		logger.debug("Export", prefix, fileName)
		
		if( fs.existsSync(fileName)) {
			return sendFile(res, fileName)
		} 
		
		function CreateShapeFile(shpDir, jsonFileName, zipFileName, cb) {
			try {
				if( !fs.existsSync(shpDir)) fs.mkdirSync(shpDir)
				var cmd = "ogr2ogr -f 'ESRI Shapefile' " + shpDir + " " + jsonFileName + ";\n"
				cmd += "cd "+shpDir+"/..;\n"
				cmd += "zip "+zipFileName+ " shp/*;\n"
				cmd += "rm -rf "+shpDir+";\n"
				exec(cmd, function (error, stdout, stderr) {
					logger.info("convert", error, stdout, stderr)
					cb(error)
				})
			} catch(e) {
				logger.error("Error converting to Shape file", e)
				cb(500)
			}	
		}

		function CreateOSMFile(jsonFileName, osmbz2FileName, cb) {
			try {
				var osmFileName = osmbz2FileName.replace(".bz2","")
			
				var geojson	= JSON.parse(fs.readFileSync(jsonFileName, "utf8"));	
				var osm 	= osm_geojson.geojson2osm(geojson)
				fs.writeFileSync(osmFileName, osm, "utf8");	
			
				var cmd = "bzip2 "+osmFileName+ " ;\n"
				exec(cmd, function (error, stdout, stderr) {
					logger.debug("convert", error, stdout, stderr)
					cb(error)
				})
			} catch(e){
				logger.error("Error converting to OSM file", e)
				cb(500)
			}	
		}
		
		if( prefix.indexOf(".shp.zip") > 0) {
			// See if geojson file is there
			var newprefix 			= prefix.replace("shp.zip","geojson")
			var geojsonfileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
			var shpDir		 		= path.join(tmp_dir, bucket, subfolder, year, doy, "shp")
			if( !fs.existsSync(geojsonfileName)) {
				var newprefix 		= prefix.replace("shp.zip","topojson.gz")
				var topofileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
				DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, geojsonfileName, bucket, subfolder, year, doy, newprefix, function(err, geojson) {
					CreateShapeFile(shpDir, geojsonfileName, fileName, function(err) {
						sendFile(res, fileName)
					})	
				})
			} else {
				CreateShapeFile(shpDir, geojsonfileName, fileName, function(err) {
					sendFile(res, fileName)
				})	
			}
		} else if( prefix.indexOf(".geojson") > 0) {
			var geojsonfileName = fileName

			var newprefix 		= prefix.replace("geojson","topojson.gz")
			var topofileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
			
			DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, geojsonfileName, bucket, subfolder, year, doy, newprefix, function(err, geojson) {
				if( !err ) {
					 res.setHeader("Content-Type", "application/json")
					 return res.json(geojson)
				 } else {
			 		 res.sendStatus(err)
				 }
			})
		} else if( prefix.indexOf(".arcjson") > 0 ) {
			var newprefix 		= prefix.replace("arcjson","geojson")
			var geojsonfileName = path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
			
			var newprefix 		= prefix.replace("arcjson","topojson.gz")
			var topofileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
			logger.debug("export to arcjson from", topofileName)
			
			DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, geojsonfileName, bucket, subfolder, year, doy, newprefix, function(err, geojson) {
				if( !err ) {
					// convert to Arc JSON
					//var options = {"idAttribute": "FID"}
					
					var id 		= 1
					for (var f in geojson.features ) {
						geojson.features[f].id = id
						id += 1
					}
					
					var arcjson = Terraformer.ArcGIS.convert(geojson)
					if( !err ) {
						 res.setHeader("Content-Type", "application/json")
						 return res.json(arcjson)
					 }
			 	} else {
			 		logger.error("Got err from DownloadTopojsonFilefromS3andConvertToGeoJSON", err)
			 	}
	 		 	res.sendStatus(err)
			})
		} else if( prefix.indexOf(".osm.bz2") > 0 ) {
			// See if geojson file is there
			var newprefix 			= prefix.replace("osm.bz2","geojson")
			var geojsonfileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
			if( !fs.existsSync(geojsonfileName)) {
				var newprefix 		= prefix.replace("osm.bz2","topojson.gz")
				var topofileName 	= path.join(tmp_dir, bucket, subfolder, year, doy, newprefix)
				DownloadTopojsonFilefromS3andConvertToGeoJSON(topofileName, geojsonfileName, bucket, subfolder, year, doy, newprefix, function(err, geojson) {
					CreateOSMFile(geojsonfileName, fileName, function(err) {
						if(!err) {
							sendFile(res, fileName)
						} else {
							res.sendStatus(err)
						}
					})	
				})
			} else {
				CreateOSMFile(geojsonfileName, fileName, function(err) {
					if( !err ) {
						sendFile(res, fileName)
					} else {
						res.sendStatus(err)
					}
				})	
			}
		} else {
			res.sendStatus(500)			
		}
	}
	
	Query.prototype.Browse= function(req,res) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prefix 		= req.params['prefix']
		
		var date;
		if( year != '-') {
			date	 		= moment(year+"-"+doy)
		} else {
			date = moment()
		}
		
		var host 		= req.protocol + "://"+ req.get('Host')
		var legend		= "legend."+ this.options.product+".title"
		var slf 		= this
		
		//this.CheckEmptyBucketList(bucket, prefix, function() {
		this.ListObjects(bucket, prefix, function() {
			var key 		=  slf.options.subfolder + "/" + date.year() + "/" + doy + "/"
			var artifacts	= slf.bucketList[key]
					
			//var region 	= {
			//	name: 	req.gettext(legend),
			//	scene: 	year+"-"+doy,
			//	bbox: 	this.options.bbox,
			//	target: this.options.target
			//}
		
			var jday	= date.dayOfYear()
			if( jday < 10 ) {
				jday = "00"+jday
			} else if( jday < 100 ) jday = "0"+jday

			var month = date.month() + 1
			if( month < 10 ) month = "0"+ month

			var day		= date.date();
			if( day < 10 ) day = "0"+day
			
			if( slf.options.bucket === "ojo-*" ) {
				slf.options.bucket = region.bucket
			}
						
			var json_product;
			
			if( slf.options.bucket != undefined ) {
				var s3host				= "https://s3.amazonaws.com/"+ bucket+"/"+slf.options.subfolder+"/" + year + "/" + jday + "/"

				// local host cache for S3
				var s3proxy				= host+'/products/s3/'+regionKey+"/"+ slf.options.subfolder+"/"+year+"/"+jday + "/"

				var thn_ext				= slf.options.browse_img || "_thn.jpg"
				
				var browse_img			= _.find(artifacts, function(el) { 
								return (el.key.indexOf(thn_ext) > 0) || (el.key.indexOf("_thn.jpg") > 0)
							}).key
						
				var products		= _.find(artifacts, function(el) { return el.key.indexOf("topojson.gz") > 0 })
				if( products ) {
					json_product = products.key
				} else {
					products		= _.find(artifacts, function(el) { return el.key.indexOf("geojson.gz") > 0 })
					if( products ) {
						json_product = products.key
					}
				}
					
				var data_url			= s3proxy+json_product || slf.options.geojson
			} else {
				s3proxy			 	= ""
				browse_img			= host + slf.options.browse_img
				json_product		= host + "/products/s3/Global/landslide_catalog/-/-/landslide_catalog.geojson"
				data_url			= json_product
			}
												
			var product_title 		= slf.options.product
			var product_description	= req.gettext(legend)
						
			if( slf.options.prefix_map ) {
				var str = "legend."+product_title+"."+prefix
				product_description	= req.gettext(str)
			}
						
			res.render("products/s3_product", {
				social_envs: 	app.social_envs,
				description: 	product_description + " - " + date.format("YYYY-MM-DD"),
				image: 			s3proxy+browse_img,
				product_title: 	product_title,
				product_tags: 	slf.options.tags.join(","),
				url: 			host+"/products/" + slf.options.subfolder +"/browse/"+ regionKey +"/" + year+"/"+doy+"/"+prefix,
				map_url: 		host+"/products/"+ slf.options.subfolder + "/map/"+regionKey+"/"+year+"/"+doy+"/"+prefix,
				date: 			date.format("YYYY-MM-DD"),
				region: 		region,
				data: 			slf.options.original_url,
				topojson: 		data_url,
				layout: 		false
			})
		})
	},
	
	Query.prototype.MapInfo= function(req, res) {
		var style 	= this.options.style(req);
		var  html  	= this.options.legend(req);
		var credits = this.options.credits(req);
		
		res.render("mapinfo/"+this.options.subfolder, { style: style, html: html, credits: credits })
	}
	
	Query.prototype.Style= function (req, res) {
		var json = this.options.style(req)
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(json)
	}
	
	Query.prototype.Legend= function(req, res) {
		var html = this.options.legend(req)
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'text/html');		
		res.send(html)
	}
	
	Query.prototype.Credits= function(req, res) {
		var str = this.options.credits(req)
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	}
	
	Query.prototype.Metadata= function(req, res) {
		var str = this.options.metadata ? this.options.metadata(req) : {}
		
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	}
	
	module.exports 		= Query;