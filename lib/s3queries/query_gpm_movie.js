var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	_			= require('underscore'),
	Hawk		= require('hawk'),
	mkdirp		= require('mkdirp'),
	filesize 	= require('filesize'),
	Query		= require('./query_s3'),
	exec 		= require('child_process').exec,
	as			= require("../activitystreams.js"), 
	geohash		= require('ngeohash')
	;
	
	var	bbox		=	[60, 40, 80, 20];				// lng,lat bottom left - top right
	var	centerlon	=  	(bbox[0]+bbox[2])/2;
	var	centerlat	=	(bbox[1]+bbox[3])/2;
	
	var source_url 	= "http://pmm.nasa.gov/"
	
	var options = {
		bucket: 		'ojo-global',
		subfolder: 		'gpm_mov',
		browse_img: 	"_thn.png",
		geojson: 		undefined,
		topojson: 		undefined,
		topojson_gz: 	undefined,
		geotiff: 		undefined,
		mpg: 			'.mpg',
		source: 		'sources.gpm',
		sensor: 		'sensors.gpm',
		resolution: 	'1000m',
		original_url:   source_url,
		product: 		'precip_movie',
		tags: 			['precip_movie', 'precipitation', 'rainfall'],
		bbox: 			bbox,							// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		6
	}
	
	var colors = ["#f7fcf0","#e0f3db","#ccebc5","#a8ddb5","#7bccc4","#4eb3d3","#2b8cbe","#0868ac","#084081","#810F7C","#4D004A"	]

	options.exports =  [
			{ 
				'ext': 'mpg',
				'mediaType': "video/mp4"
			}
		]
		
	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.precipitation_gpm.credits"),
			"url": 		source_url
		};
		return json;
	}

	options.legend = function(req) {
		var html = "<style id='precipitation_legend_style' >"
	    html += ".precipitation_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".precipitation_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".precipitation_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".precipitation_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".precipitation_map-info {"
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
	
		html += "<div id='precipitation_legend' class='precipitation_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.precipitation_gpm.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><span style='background: " + colors[10] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.377mm") +"</li>"
		html += "	   <li><span style='background: " + colors[9] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.233mm") +"</li>"
		html += "	   <li><span style='background: " + colors[8] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.144mm") +"</li>"
		html += "	   <li><span style='background: " + colors[7] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.89mm") +"</li>"
		html += "	   <li><span style='background: " + colors[6] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.55mm") +"</li>"
		html += "	   <li><span style='background: " + colors[5] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.34mm") +"</li>"
		html += "	   <li><span style='background: " + colors[4] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.21mm") +"</li>"
		html += "	   <li><span style='background: " + colors[3] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.13mm") +"</li>"
		html += "	   <li><span style='background: " + colors[2] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.8mm") +"</li>"
		html += "	   <li><span style='background: " + colors[1] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.5mm") +"</li>"
		html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.3mm") +"</li>"
		//html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.2mm") +"</li>"
		//html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_gpm.legend.1mm") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.precipitation_gpm.source.label")+": <a href='"+source_url+"'>"+ req.gettext("legend.precipitation_gpm.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
	
		//console.log("legend title", req.gettext("legend.precipitation_gpm.title"))
	
		return html
	}
	
	options.metadata = function(req) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prefix 		= req.params['prefix']
		
		var product 			= prefix
		var legend				= "legend."+ options.product+"."+prefix
		var product_description	= req.gettext(legend)
		var url					= req.url
		var host 				= req.protocol + "://"+ req.get('Host')
		
		var accrualPeriodicity	= "N/A";

		if( prefix == "gpm_1d") {
			accrualPeriodicity = "R/P1D"
		} else if( prefix == "gpm_3d") {
			accrualPeriodicity = "R/P3D"
		} else if(prefix == "gpm_7d") {
			accrualPeriodicity = "R/P7D"
		}
		
		var json = {
			"@context": 	"https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
			"@id": 			"http://www.agency.gov/data.json",
			"@type": 		"dcat:Catalog",
			"conformsTo": 	"https://project-open-data.cio.gov/v1.1/schema",
			"describedBy": 	"https://project-open-data.cio.gov/v1.1/schema/catalog.json",
			"dataset": [
				{
					"@type": "dcat:Dataset",
		            "accessLevel": "public",
					"accrualPeriodicity": accrualPeriodicity,
		            "bureauCode": [
		                "026:00"
		            ],
		            "contactPoint": {
		                "fn": "Dalia Kirschbaum",
		                "hasEmail": "mailto:dalia.b.kirschbaum@nasa.gov"
		            },
		            "description": "This dataset provides global merged rainfall data from Precipitation Measurement Missions",
		            "distribution": [
		                {
		                    "downloadURL": "http://pmm.nasa.gov/data-access/downloads/gpm",
		                    "mediaType": "html"
		                }
		            ],
		            "identifier": url,
		            "keyword": [
		                "rainfall",
		                "precipitation",
		                "droughts",
		                "floods",
		                "hurricanes",
		                "IMERG",
		                "GPM"
		            ],
					"landingPage": host,
					"language": [
					    "en-US"
					],
					"license": "http://creativecommons.org/publicdomain/zero/1.0/",
		            "modified": "2015-08-29T15:03:00Z",
		            "programCode": [
		                "026:006"
		            ],
		            "publisher": {
		                "name": "Precipitation Measurement Missions",
		                "subOrganizationOf": {
		                    "name": "Goddard Space Flight Center",
		                    "subOrganizationOf": {
		                        "name": "NASA"
		                    }
		                }
		            },
		            "title": 	"1-Day Rainfall Accumulation",
					"rights": 	"This dataset has been given an international public domain dedication for worldwide reuse",
					"spatial": 	"Global",
					"dataQuality": true,
					"webService": host+"/opensearch"
		        }
		    ]
		}
		json.dataset[0].keyword.push(product)
		json.dataset[0].title = product_description
		return json
	}
	
	function InBBOX( lat, lon, bbox) {
		if( (lat > bbox[1]) && (lat< bbox[3]) && (lon > bbox[0]) && (lon < bbox[2]) ) return true;
		return false
	}
	
	function FindRegionKey(lat, lon) {
		// let's try to find a region, otherwise return global
		var global = 'Global'
		return global
	}
	
	Query.prototype.MovieQueryAll= function(req, user, credentials, host, query, bbox, lat, lon, startTime, endTime, startIndex, itemsPerPage, limit, cb ) {
		var err 	= 0;
		var json 	= {
			replies: {
				items: []
			}
		}
		
		if( query != "precip_movie") {
			return cb(err, json)	
		}
			
		console.log( "MovieQueryAll", query, bbox, lat, lon, startTime.format(), endTime.format())

		var zoomLevel;
		var latMax, latMin;
		
		if( bbox[1] > bbox[3]) {
			latMax = bbox[1]
			latMin = bbox[3]
		} else {
			latMax = bbox[3]
			latMin = bbox[1]			
		}
		
		var latDiff = latMax - latMin;
		var lngDiff = bbox[2] - bbox[0];

		var maxDiff = (lngDiff > latDiff) ? lngDiff : latDiff;
		if (maxDiff < 360 / Math.pow(2, 20)) {
		    zoomLevel = 21;
		} else {
		    zoomLevel = parseInt((-1*( (Math.log(maxDiff)/Math.log(2)) - (Math.log(360)/Math.log(2)))));
		    if (zoomLevel < 1)
		        zoomLevel = 1;
		}
		console.log("ZoomLevel:", zoomLevel)
	
		
		// see https://github.com/sunng87/node-geohash
		// https://github.com/davetroy/geohash-js
		
		var gh			= geohash.encode(lat,lon,zoomLevel)
		var movie_file 	= "movie.mp4"		
		var prefix 		= this.options.product
		var tmpDir		= this.options.product + "_" + startTime.format("YYYYMMDD") + "_" + endTime.format("YYYYMMDD")+"_"+gh
			
		var outputDir 	= path.join(app.get("tmp_dir"), "gpm", tmpDir)
		var s3_proxy	= host+'/products/s3/tmp/gpm/-/'+tmpDir
		var	ymd			= startTime.format("YYYYMMDD")+'_'+endTime.format("YYYYMMDD") 
				
		// Check if directory is there
		// if not, run python script
		if( !fs.existsSync(outputDir)) {
			// python gpm_movie.py --startTime 2016-01-12 --endTime 2016-01-15 --zoom 7 --lat -20.6332733 --lon -42.0 --outputDir ../tmp/tmpkq9U7I -v
			mkdirp.sync(outputDir)
			
			var cmd = "python ./python/gpm_movie.py"
			cmd += " --startTime " + startTime.format("YYYY-MM-DD")
			cmd += " --endTime " + endTime.format("YYYY-MM-DD")
			cmd += " --zoom " + zoomLevel
			cmd += " --lat " + lat
			cmd += " --lon " + lon
			cmd += " --outputDir " + outputDir
			cmd += " > " + outputDir + "/movie.log"
			console.log(cmd)
			
			exec(cmd, function (error, stdout, stderr) {
				console.log("python err", error, stdout, stderr)
			})
			
			var entry = as.entry(tmpDir, "geoss:"+ this.options.product, this.options.product)
				.addImage(outputDir + "/movie.jpg")
				.geometry_bbox(bbox)
				.addProperty("source", 		req.gettext("properties.source"),	 	"NASA GSFC GPM")				
				.addProperty("url", 		req.gettext("properties.url"), 			"http://pmm.nasa.gov/")				
				.addProperty("sensor",  	req.gettext("properties.sensor"), 		"GPM")
				.addProperty("date", 		req.gettext("properties.date"), 		ymd)				
				.addProperty("resolution", 	req.gettext("properties.resolution"), 	"1000m")	
			
			var browse = as.action(req.gettext("actions.browse"),"ojo:browse")
				.addHttpGet("log in progress", outputDir + "/movie.log")

			entry.addAction(browse)
			debug("entry", entry.stringify())

			json.replies.items.push(entry)	
			return cb(err, json)	
		}
		
		try {
			var stats 		= fs.statSync(path.join(outputDir,movie_file))
			//console.log(stats)
			var size		= stats.size
			var browse_img	= s3_proxy + "/movie.jpg"
			var prefix 		= this.options.product
						
			var source 		= req.gettext(this.options.source)
			var sensor 		= req.gettext(this.options.sensor)
			var url 		= this.options.original_url

			var properties 	= properties
			var downloads	= []
			var browse_lnk 	= prefix
			var movie_file 	= s3_proxy + "/movie.mp4"
			
			var id			= prefix+"_"+ymd
			var name		= (this.options.displayName || prefix)+"_"+ymd
			var entry 		= as.entry(id, "geoss:"+ this.options.product, name)
				.addImage(browse_img)
				.geometry_bbox(bbox)
				.addProperty("source", 		req.gettext("properties.source"),	 	"NASA GSFC GPM")				
				.addProperty("url", 		req.gettext("properties.url"), 			"http://pmm.nasa.gov/")				
				.addProperty("sensor",  	req.gettext("properties.sensor"), 		"GPM")
				.addProperty("date", 		req.gettext("properties.date"), 		ymd)				
				.addProperty("resolution", 	req.gettext("properties.resolution"), 	"1000m")	
			
			var browse 		= as.action("ojo:browse", req.gettext("actions.browse"))
				.addHttpGet("movie", movie_file)
			
			var fsize 		=	filesize( size, {round:2, suffixes: {
									"B": req.gettext("filesize.B"), 
									"kB": req.gettext("filesize.KB"), 
									"MB": req.gettext("filesize.MB"), 
									"GB": req.gettext("filesize.GB"), 
									"TB": req.gettext("filesize.TB")
								}})
								
			var downloads 	= as.action(req.gettext("actions.download"),"ojo:download")
				.addHttpGet("movie", movie_file, fsize)
				.addHttpGet("log", movie_file.replace(".mp4", ".log"))
			
			entry.addAction(browse)
				.addAction(downloads)
								
			//debug(JSON.stringify(entry,null,'\t'))
			json.replies.items.push(entry)
			
		} catch(e) {
			console.log(e)
		}
		return cb(err, json)
	}
	
	
	var query					= new Query(options)
    query.source				= "gpm"
    query.FindRegionKey			= FindRegionKey
	query.QueryAll				= query.MovieQueryAll
	
	module.exports.query		= query;
