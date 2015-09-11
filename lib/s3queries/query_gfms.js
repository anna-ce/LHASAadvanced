//
//	Support GFMS Flood Nowcast from UMD
//

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
	
	var source_url = "http://flood.umd.edu/"
	
	var options = {
		bucket: 		'ojo-global',
		subfolder: 		'gfms',
		browse_img: 	"_thn.jpg",
		geojson: 		undefined,
		topojson: 		".topojson",
		topojson_gz: 	".topojson.gz",
		//shape_gz:  		".shp.gz",
		shape_zip: 		undefined,
		geotiff: 		".tif",
		source: 		'sources.gfms',
		sensor: 		'sensors.gfms',
		resolution: 	'14km',
		original_url:   source_url,
		product: 		'flood_nowcast',
		tags: 			['flood_nowcast', 'flood'],
		bbox: 			bbox,							// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		2,
		attributes: [
			{
				"name": "flood",
				"type": "esriFieldTypeInteger"
			}
		],
		prefix_map: 	{
			'flood_nowcast': 'flood_14km'
		}
	}
	
	var colors  	= [ "#FF0000",  "#FFA500", "#FFD700", 	"#0000FF", "#00BFFF", 	"#00FF00"]

	options.exports =  [
			{ 
				'ext': 'geojson',
				'mediaType': "application/json"
			},
			{ 
				'ext': 'shp.zip',
				'mediaType': "application/zip"
			},
		]

	options.subset_action 	= true
	options.esri 			= true

	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.flood_nowcast.credits"),
			"url": 		source_url
		};
		return json;
	}
	options.style = function(req) {
		var json = {
			"{flood}==200": {
				color: colors[0], 	
				weight: 2
			},
			"{flood}==100": {
				color: colors[1], 	
				weight: 2
			},
			"{flood}==50": {
				color: colors[2], 	
				weight: 2
			},
			"{flood}==20": {
				color: colors[3], 	
				weight: 2
			},
			"{flood}==10": {
				color: colors[4], 	
				weight: 2
			},
			"{flood}==5": {
				color: colors[5], 	
				weight: 2
			}
		}
		return json
	}

	options.legend = function(req) {
		var html = "<style id='flood_nowcast_legend_style' >"
	    html += ".flood_nowcast_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".flood_nowcast_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".flood_nowcast_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".flood_nowcast_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".flood_nowcast_map-info {"
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
	
		html += "<div id='flood_nowcast_legend' class='flood_nowcast_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.flood_nowcast.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><span style='background: " + colors[5] + "'></span>&nbsp;"+ req.gettext("legend.flood_nowcast.legend.5mm") +"</li>"
		html += "	   <li><span style='background: " + colors[4] + "'></span>&nbsp;"+ req.gettext("legend.flood_nowcast.legend.10mm") +"</li>"
		html += "	   <li><span style='background: " + colors[3] + "'></span>&nbsp;"+ req.gettext("legend.flood_nowcast.legend.20mm") +"</li>"
		html += "	   <li><span style='background: " + colors[2] + "'></span>&nbsp;"+ req.gettext("legend.flood_nowcast.legend.50mm") +"</li>"
		html += "	   <li><span style='background: " + colors[1] + "'></span>&nbsp;"+ req.gettext("legend.flood_nowcast.legend.100mm") +"</li>"
		html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.flood_nowcast.legend.200mm") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.flood_nowcast.source.label")+": <a href='"+source_url+"'>"+ req.gettext("legend.flood_nowcast.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
	
		console.log("legend title", req.gettext("legend.flood_nowcast.title"))
	
		return html
	}
	
	options.metadata = function(req) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prefix 		= req.params['prefix']
		
		var product 			= _.invert(options.prefix_map)[prefix]
		var legend				= "legend."+ options.product+"."+prefix
		var product_description	= req.gettext(legend)
		var url					= req.url
		var host				= req.headers.host
		
		var accrualPeriodicity	= "R/P1D";
		
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
		                "fn": "Dr Bob Adler",
		                "hasEmail": "mailto:radler@umd.edu"
		            },
		            "description": "This dataset provides global flood monitoring from a model running at University of maryland",
		            "distribution": [
		                {
		                    "downloadURL": "http://flood.umd.edu/",
		                    "mediaType": "html"
		                }
		            ],
		            "identifier": url,
		            "keyword": [
		                "rainfall",
		                "precipitation",
		                "droughts",
		                "floods",
		                "IMERG",
		                "GPM"
		            ],
					"landingPage": "http://ojo-bot.herokuapp.com",
					"language": [
					    "en-US"
					],
					"license": "http://creativecommons.org/publicdomain/zero/1.0/",
		            "modified": "2015-08-29T15:03:00Z",
		            "programCode": [
		                "026:006"
		            ],
		            "publisher": {
		                "name": "Earth System Science Interdisciplinary Center",
		                "subOrganizationOf": {
		                    "name": "University of Maryland"
		                }
		            },
		            "title": 	"Global Flood Monitoring",
					"rights": 	"This dataset has been given an international public domain dedication for worldwide reuse",
					"spatial": 	"Global",
					"dataQuality": true,
					"webService": "http://"+host+"/opensearch"
		        }
		    ]
		}
		json.dataset[0].keyword.push(product)
		json.dataset[0].title = product_description
		return json
	}
	
	function FindRegionKey(lat, lon) {
		console.log("Global Region")
		var r = 'Global'
		return r
	}
	
	var query					= new Query(options)
    query.source				= "gfms"
    query.FindRegionKey			= FindRegionKey
	module.exports.query		= query;
