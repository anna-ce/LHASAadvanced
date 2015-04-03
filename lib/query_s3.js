var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	_			= require('underscore'),
	Hawk		= require('hawk'),
	filesize 	= require('filesize'),
	query_s3	= require('../lib/query_s3')
	;
		
	function padDoy( doy ) {
		if( doy < 10 ) {
			doy = "00"+doy
		} else if( doy < 100 ) {
			doy = "0"+doy
		}
		return doy
	}
	
	var Query = function( options ) {
		this.options 		= options
		this.bucketList 	= {}
	}
	
	//
	// List all objects in bucket/subfolder
	//
	Query.prototype.ListObjects = function( next) {
		self = this
		
		// Get a list of all objects in that bucket's subfolder (WARNING: limit=1000)
		var params = {
			Bucket: this.options.bucket,
			Prefix: this.options.subfolder
		};

		app.s3.listObjects(params, function(err, data) {
			if (err) {
				logger.error(err, err.stack); 	// an error occurred
				next(err)
			} else {
				//console.log(data);				// successful response
			
				self.bucketList = {}
				
				var contents 	= data.Contents
				_.each(data.Contents, function(elt) {
					var size 	= elt.Size
					var arr		= elt.Key.split("/")
					var name	= _.last(arr)
					var key		= elt.Key.replace(name, "")
				
					//console.log("found key", key)
				
					if( self.bucketList[key] != undefined ) {
						self.bucketList[key].push( { key: name, size: size } )
					} else {
						self.bucketList[key] = [ { key: name, size: size } ]
						//console.log("added to key", key, name)
					}					
				})
				//console.log( JSON.stringify(self.bucketList))
				next(null)
			}    
		});
	}
	
	//
	// Check if we have current list of object in bucket
	// if not, get it
	//
	Query.prototype.CheckEmptyBucketList = function(next) {
		if( _.isEmpty(this.bucketList)) {
			this.ListObjects(next)
		} else {
			next()
		}
	}
	
	Query.prototype.QueryByID = function(req, user, year, doy, credentials, cb ) {
		var date			= moment(year+"-"+doy)
		var duration		= 60 * 30
		var id				= this.options.subfolder + "_" + year.toString() + doy
		var host 			= "http://" + req.headers.host
		
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
			self.CheckIfProductInBucketList(req, key, year, month, day, jday, id, Bewit, function(err, data) {
				entry = data
				next(err)
			})
		}
		
		async.series([ 
			this.CheckEmptyBucketList.bind(this),
			checkIfProductInBucketList
		], function(err) {
			return cb(err, entry)
		})
	}
	
	Query.prototype.Check = function( req, user, d, startTime, endTime, credentials, entries, cb  ) {
		var time			= endTime.clone()
		time	 			= time.subtract(d, "days");
	
		var year 			= time.year();
		var doy  			= padDoy(time.dayOfYear());
			
		this.QueryByID(req, user, year, doy, credentials, function(err, entry) {
			if( entry ) entries.push(entry)
			cb(null)
		})
	}

	Query.prototype.CheckIfProductInBucketList = function(req, key, year, month, day, jday, id, Bewit, next) {
		if( this.bucketList[key] != undefined ) {				
			console.log("found", key)
			var artifacts			= this.bucketList[key]
			var host 				= "http://" + req.headers.host
			var date				= moment(year+"-"+jday)
		
			var s3host				= "https://s3.amazonaws.com/ojo-workshop/"+this.options.subfolder+"/"+year+"/"+jday + "/"
			var browse_img_url		= this.options.subfolder+"."+year+month+day+this.options.browse_img
				
			var downloads = []
			
			if(this.options.geojson) {
				var geojson		= this.options.subfolder+"."+year+month+day+ this.options.geojson
				var size		= "NOT FOUND"
				try {
					size =  _.find(artifacts, function(el) { return el.key == geojson }).size
				} catch(e) {
					logger.error("could not find size of", geojson)
				}
				var download_geojson = {
					"@type": 		"as:HttpRequest",
					"method": 		"GET",
					"mediaType": 	"application/json",
					"url": 			s3host+ geojson,
					"size": 		size,
					"displayName": 	req.gettext("formats.geojson")
				}
				downloads.push(download_geojson)
			}
			
			if(this.options.topojson) {
				var topojson	= this.options.subfolder+"."+year+month+day+ this.options.topojson
				var size		= "NOT FOUND"
				try {
					size 		= _.find(artifacts, function(el) { return el.key == topojson }).size
				} catch(e) {
					logger.error("could not find size of", topojson)
				}
				var download_topojson = {
					"@type": 		"as:HttpRequest",
					"method": 		"GET",
					"url": 			s3host+topojson,
					"mediaType": 	"application/json",
					"size": 		size,
					"displayName": 	req.gettext("formats.topojson")
				}
				downloads.push(download_topojson)				
			}
			
			if(this.options.topojson_gz) {
				var topojson_gz		= this.options.subfolder+"."+year+month+day+ this.options.topojson_gz
				var size			= "NOT FOUND"
				try {
					var size		= _.find(artifacts, function(el) { return el.key == topojson_gz }).size
				} catch(e) {
					logger.error("could not find size of", topojson_gz)
				}
				
				var download_topojson_gz = {
					"@type": 		"as:HttpRequest",
					"method": 		"GET",
					"url": 			s3host+ topojson_gz,
					"mediaType": 	"application/gzip",
					"size": 		size,
					"displayName": 	req.gettext("formats.topojsongz")
				}
				downloads.push(download_topojson_gz)				
			}
		
			actions = [
				{ 
					"@type": 			"ojo:browse",
					"displayName": 		req.gettext("actions.browse"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/"+ this.options.subfolder+"/browse/"+year+"/"+jday),
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
		
			var source 		= req.gettext(this.options.source)
			var sensor 		= req.gettext(this.options.sensor)

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
					"@value": this.options.resolution
				}
			}
			var bbox = this.options.bbox
			var entry = {
				"@id": 			id,
				"@type": 		"geoss:"+this.options.product,
				"displayName": 	id,
				"image": 		[ 
									{
										"url": s3host+browse_img_url,
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
			next(null, entry)
		} else {
			//console.log("not found", key)
			next(null, null)
		}
	}
	
	Query.prototype.QueryAll = function(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {		
		if( query != this.options.product) {
			logger.info("unsupported query", query)
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
	
		if( lat && (lat < this.options.bbox[3] || lat> this.options.bbox[1]) ) {
			logger.error("outside lat", lat, bbox[1], bbox[3])
			return cb(null, null)	
		}
	
		if( lon && (lon < this.options.bbox[0] || lon> this.options.bbox[2]) ) {
			logger.error("outside lon", lon)
			return cb(null, null)		
		}
			
		if( bbox ) {
			lon = (bbox[0]+bbox[2])/2
			lat = (bbox[1]+bbox[3])/2
		}
	
		var days = []
		itemsPerPage = limit;
		for( var i=0; i<itemsPerPage; i++ ) {
			days.push(i)
		}
	
		entries		= []
		
		//
		// Check every requested day
		//
		var self = this
		function checkAllRequestedDays(next) {
			async.each(days, function(d, cb2) {
				if( entries.length < limit ) {
					self.Check( req, user, d, startTime, endTime, credentials, entries, cb2) 
				} else {
					cb2(null)
				} 
			}, function(err) {
				next(null)				
			})
		}
		
		async.series([
			self.ListObjects.bind(self), 
			checkAllRequestedDays
		], function(err) {
			var json = {}
			
			if( !err ) {
				json.replies = {
					items: entries
				}
			}
			cb(err, json)			
		})
	}
	
	function render_map(region, url, req, res) {
		console.log("render_map", url)
		res.render("products/map_api", {
			region: region,
			url: url,
			layout: false
		})
	}
	
	Query.prototype.Process = function(req,res) {
	}
	
	Query.prototype.QueryProduct = function(req, res) {
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var user		= req.session.user
		var credentials	= req.session.credentials
		
		this.QueryByID(req, user, year, doy, credentials, function( err, entry ) {
			if( !err ) {
				res.json(entry)
			} else {
				console.log("no entry")
				res.sendStatus(500)
			}				
		})
	}
	
	Query.prototype.Map = function(req,res) {
		var year 	= req.params['year']
		var doy 	= req.params['doy']
		var date 	= moment(year+"-"+doy)
		var host 	= "http://"+req.headers.host
		var bbox	= bbox
		var id		= this.options.subfolder+year+"-"+doy
		
		var region 	= {
			name: 	req.gettext("legend."+this.options.product+".title")+" "+date.format(req.gettext("formats.date")),
			scene: 	id,
			bbox: 	undefined,	// feature.bbox,
			target: this.options.target,
			min_zoom: this.options.zoom
		}
		var url = host + "/products/" + this.options.subfolder + "/query/"+year+"/"+doy
		render_map(region, url, req, res )
	}
	
	Query.prototype.Browse= function(req,res) {
		var year 	= req.params['year']
		var doy 	= req.params['doy']
		var date 	= moment(year+"-"+doy)
		var host 	= "http://"+req.headers.host
		var legend	= "legend."+ this.options.product+".title"
		
		var region 	= {
			name: 	req.gettext(legend),
			scene: 	year+"-"+doy,
			bbox: 	bbox,
			target: target
		}
		
		var jday	= date.dayOfYear()
		if( jday < 10 ) {
			jday = "00"+jday
		} else if( jday < 100 ) jday = "0"+jday

		var month = date.month() + 1
		if( month < 10 ) month = "0"+ month

		var day		= date.date();
		if( day < 10 ) day = "0"+day
		
		var s3host				= "https://s3.amazonaws.com/ojo-workshop/"+ this.options.subfolder+"/" + year + "/" + jday + "/"
		var browse_img_url		= s3host+ this.options.browse_img
		
		var data_url			= s3host+this.options.topojson || this.options.geojson
		
		res.render("products/"+this.options.subfolder, {
			social_envs: 	app.social_envs,
			description: 	req.gettext(legend) +" - "+date.format("YYYY-MM-DD"),
			image: 			browse_img_url,
			url: 			host+"/products/" + this.options.subfolder +"/browse/"+year+"/"+doy,
			map_url: 		host+"/products/"+ this.options.subfolder + "/map/"+year+"/"+doy,
			date: 			date.format("YYYY-MM-DD"),
			region: 		region,
			data: 			this.options.original_url,
			topojson: 		data_url,
			layout: 		false
		})
	},
	
	
	module.exports 		= Query;