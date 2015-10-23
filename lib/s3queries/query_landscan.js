// ONRL LandScan Population Density data

var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	_			= require('underscore'),
	Hawk		= require('hawk'),
	filesize 	= require('filesize'),
	Query		= require('./query_s3')
	;
	
	var	bbox		=	[60, 40, 80, 20];				// lng,lat bottom left - top right
	var	centerlon	=  	(bbox[0]+bbox[2])/2;
	var	centerlat	=	(bbox[1]+bbox[3])/2;
	
	var source_url	= 'http://web.ornl.gov/sci/landscan/'
	
	var options = {
		bucket: 		'ojo-*',
		subfolder: 		'ls',
		browse_img: 	"_thn.jpg",
		geojson: 		undefined,
		topojson: 		".topojson",
		topojson_gz: 	".topojson.gz",
		shape_zip: 		undefined,
		geotiff: 		".tif",
		source: 		'sources.ls',
		sensor: 		'sensors.ls',
		resolution: 	'30 arcsec ~1km',
		original_url:   source_url,
		product: 		'population_count',
		tags: 			['landscan', 'ls', 'population_count'],
		bbox: 			bbox,							// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		6,
		displayName: 	"population density",
		prefix_map: 	{
			'population_count': 'ls'
		}
	}
	
	levels 				= [ 5500, 3400, 2100, 1300, 800, 500, 300, 200, 100 ]
	
	// From http://colorbrewer2.org/	
	var colors 			= [	"#f7f4f9", "#e7e1ef", "#d4b9da", "#c994c7", "#df65b0", "#e7298a", "#ce1256", "#980043", "#67001f"]
	
	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.population_count.credits"),
			"url": 		source_url,
		};
		return json;
	}
	
	options.style = function(req) {
		var json = {
			"{population}==100": {
				color: colors[0], 	
				weight: 2
			},
			"{population}==200": {
				color: colors[1], 	
				weight: 2
			},
			"{population}==300": {
				color: colors[2], 	
				weight: 2
			},
			"{population}==500": {
				color: colors[3], 	
				weight: 2
			},
			"{population}==800": {
				color: colors[4], 	
				weight: 2
			},
			"{population}==1300": {
				color: colors[5], 	
				weight: 2
			},
			"{population}==2100": {
				color: colors[6], 	
				weight: 2
			},
			"{population}==3400": {
				color: colors[7], 	
				weight: 2
			},
			"{population}==5500": {
				color: colors[8], 	
				weight: 2
			}
		}
		return json
	}
	
	options.legend = function(req) {
		var html = "<style id='pop_legend_style' >"
	    html += ".pop_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".pop_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".pop_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".pop_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".pop_map-info {"
		html += "    padding: 6px 8px;"
		html += "    font: 14px/16px Arial, Helvetica, sans-serif;"
		html += "    background: white;"
		html += "    background: rgba(255,255,255,0.8);"
		html += "    box-shadow: 0 0 15px rgba(0,0,0,0.2);"
		html += "    border-radius: 5px;"
		html += "	 position: relative;"
		html += "	 float: right;"
		html += "    line-height: 18px;"
		html += "    color: #555;"
	
		html += "}"
		html += "</style>"
	
		html += "<div id='pop_map_legend' class='pop_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.population_count.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><span style='background: " + colors[8] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.5500") +"</li>"
		html += "	   <li><span style='background: " + colors[7] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.3400") +"</li>"
		html += "	   <li><span style='background: " + colors[6] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.2100") +"</li>"
		html += "	   <li><span style='background: " + colors[5] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.1300") +"</li>"
		html += "	   <li><span style='background: " + colors[4] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.800") +"</li>"
		html += "	   <li><span style='background: " + colors[3] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.500") +"</li>"
		html += "	   <li><span style='background: " + colors[2] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.300") +"</li>"
		html += "	   <li><span style='background: " + colors[1] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.200") +"</li>"
		html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.population_count.legend.100") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.population_count.source.label")+": <a href='" + source_url + "'>"+ req.gettext("legend.population_count.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
		
		return html
	}
	
	Query.prototype.LandScanQueryAll= function(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
		
		var regionKey  	= this.FindRegionKey(lat, lon)
		if(regionKey == undefined )	{
			logger.error("Undefined RegionKey", lat, lon)
			return cb(null, null)
		}
			
		var bucket		= app.config.regions[regionKey].bucket
		var entries		= []
		var self		= this
		
		console.log("LandScanQueryAll", regionKey);
		
		function Bewit(url) {
			if( credentials ) {
				var bewit = Hawk.uri.getBewit(url, { credentials: credentials, ttlSec: duration, ext: user.email })
				url += "?bewit="+bewit
			}
			return url;
		}
		
		self.ListObjects(bucket, 'ls', function(err) {
			var year 	= '2011'
			var doy		= '-'
			var id		= "pop_2011"
			
			var artifacts	= self.bucketList['ls/2011/']
			
			var s3host				= "https://s3.amazonaws.com/"+bucket+"/ls/2011/"
			var s3proxy				= host+'/products/'+regionKey+"/query/pop/2011/"
			
			var browse_img			= "ls.2011_thn.jpg"
			var topojson_file		= "ls.2011.topojson"
			var topojson_gz_file	= "ls.2011.topojson.gz"
			
			console.log(artifacts)
			
			var topojson_size		= _.find(artifacts, function(el) { return el.key == topojson_file}).size
			var topojson_gz_size	= _.find(artifacts, function(el) { return el.key == topojson_gz_file }).size
			
			console.log(s3host, browse_img)
			
			actions = [
				{ 
					"@type": 			"ojo:browse",
					"displayName": 		req.gettext("actions.browse"),
					"using": [{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			Bewit(host+"/products/ls/browse/"+regionKey+"/"+year+"/"+doy+"/ls"),
						"mediaType": 	"html"
					}]
				},
				{
					"@type": 			"ojo:download",
					"displayName": 		req.gettext("actions.download"),
					"using": [
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			Bewit(s3proxy+topojson_file),
							"mediaType": 	"application/json",
							"size": 		filesize(topojson_size),
							"displayName": 	req.gettext("formats.topojson")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"url": 			Bewit(s3proxy+topojson_gz_file),
							"mediaType": 	"application/gzip",
							"size": 		filesize(topojson_gz_size),
							"displayName": 	req.gettext("formats.topojsongz")
						}	
					]
				},
				{
					"@type": 			"ojo:map",
					"displayName": 		req.gettext("actions.map"),
					"using": [
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"legend",
							"url": 			host+"/mapinfo/ls/legend",
							"mediaType": 	"text/html",
							"displayName": 	req.gettext("mapinfo.legend")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"style",
							"url": 			host+"/mapinfo/ls/style",
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("mapinfo.style")
						},
						{
							"@type": 		"as:HttpRequest",
							"method": 		"GET",
							"@id": 			"credits",
							"url": 			host+"/mapinfo/ls/credits",
							"mediaType": 	"application/json",
							"displayName": 	req.gettext("mapinfo.credits")
						}
					]
				}
			]
			
			var source 		= req.gettext("sources.ls")
			var sensor 		= req.gettext("sensors.ls")
	
			var properties = {
				"source": {
					"@label": req.gettext("properties.source"),
					"@value": source
				},
				"date": {
					"@label": req.gettext("properties.date"),
					"@value": 2011
				},
				"resolution": {
					"@label": req.gettext("properties.resolution"),
					"@value": "30 arc-second or about 1km"
				}
			}
				
			var entry = {
				"@id": 			id,
				"@type": 		"geoss:population_count",
				"displayName": 	id,
				"image": 		[ 
									{
										"url": s3host+browse_img,
										"mediaType": "image/png",
										"rel": "browse"
									}
								],
				"properties": 		properties,
				"geometry": {
					"type": "Polygon",
					"coordinates": [[
						[40, 60],
						[40, 80],
						[20, 80],
						[20, 60],
						[40, 60]
					]]
				},
				"action": 			actions
			}
			
			var json = {
				replies: {
					items: [entry]
				}
			}
			
			return cb(err, json)
		})
	}	
		
	var query				= new Query(options)
	query.source			= "landscan"
	query.QueryAll			= query.LandScanQueryAll
	module.exports.query 	= query;