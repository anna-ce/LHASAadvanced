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
	
	var source_url = "http://srt.marn.gob.sv/"
	
	var options = {
		subfolder: 		'wrf_30km',	
		browse_img: 	"_thn.jpg",
		geojson: 		undefined,
		topojson: 		undefined,
		topojson_gz: 	".topojson.gz",
		geotiff: 		".tif",
		source: 		'sources.wrf',
		sensor: 		'sensors.wrf',
		resolution: 	'30km',
		original_url:   source_url,
		product: 		'precipitation',
		tags: 			['precip_1d_forecast', 'precipitation', 'rainfall', 'forecast', 'wrf'],
		minzoom: 		6,
		attributes: [
			{
				"name": "precip",
				"type": "esriFieldTypeInteger"
			}
		],
		prefix_map: 	{
			'precip_1d_forecast': 	'fct_precip_1d'
		}
	}

	levels				= [ 377, 		233, 		144, 		89, 		55, 		34, 		21, 		13, 		8, 			5,			3]
	colors 				= ["#4D004A",	"#810F7C",	"#084081",	"#0868ac",	"#2b8cbe",	"#4eb3d3",	"#7bccc4",	"#a8ddb5",	"#ccebc5",	"#e0f3db", "#f7fcf0"]
		
	var wrf_1d_text 	= [ "legend.precipitation_wrf_30km.legend.377", 
							"legend.precipitation_wrf_30km.legend.233",
							"legend.precipitation_wrf_30km.legend.144",
							"legend.precipitation_wrf_30km.legend.89",
							"legend.precipitation_wrf_30km.legend.55",
							"legend.precipitation_wrf_30km.legend.34",
							"legend.precipitation_wrf_30km.legend.21",
							"legend.precipitation_wrf_30km.legend.13",
							"legend.precipitation_wrf_30km.legend.8",
							"legend.precipitation_wrf_30km.legend.5",
							"legend.precipitation_wrf_30km.legend.3"]
		
	
	var json_1d 			= {}
	
	function build_json(json, levels) {
		for( var i in levels) {
			var level = levels[i]
			var hash  = "{precip}=="+level
			json[hash] = {
				color: colors[i], 	
				fillOpacity: 0.5,
				weight: 2
			}
			if( i == 0 ) json[hash].weight = 0
		}		
	}
	
	build_json(json_1d, 	levels)
	
	options.exports =  [
		{ 
			'ext': 'geojson',
			'mediaType': "application/json"
		},
		{ 
			'ext': 'arcjson',
			'mediaType': "application/json"
		},
		{ 
			'ext': 'shp.zip',
			'mediaType': "application/zip"
		}
	]

	options.subset_action 	= true
	options.esri 			= true
		
	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.precipitation_wrf_30km.credits"),
			"url": 		source_url
		};
		return json;
	}
	
	options.style = function(req) {
		var product = req.query.product.split('.')[0]
	
		return json_1d
	}

	options.legend = function(req) {
		var product = req.query.product.split('.')[0]
		var text  	= wrf_1d_text;
		
		var html = "<style id='precipitation_legend_style' >"
	    html += ".wrf_precipitation_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".wrf_precipitation_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".wrf_precipitation_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".wrf_precipitation_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".wrf_precipitation_map-info {"
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
	
		html += "<div id='precipitation_legend' class='wrf_precipitation_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.precipitation_wrf_30km.fct_precip_1d")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		
		for( var i in colors) {
			var t= "	   <li><span style='background: " + colors[i] + "'></span>&nbsp;"+ req.gettext(text[i]) +"</li>"
			html += t
		}
		
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.precipitation_wrf_30km.source.label")+": <a href='"+source_url+"'>"+ req.gettext("legend.precipitation_wrf_30km.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
		
		return html
	}
	
	options.metadata = function(req) {
		var regionKey			= req.params['regionKey']
		var region				= app.config.regions[regionKey]
		var bucket				= region.bucket
		var year 				= req.params['year']
		var doy 				= req.params['doy']
		var prefix 				= req.params['prefix']
		
		var product 			= _.invert(options.prefix_map)[prefix]
		var legend				= "legend."+ options.product+"."+prefix
		var product_description	= req.gettext(legend)
		var url					= req.url
		var host 				= req.protocol + "://"+ req.get('Host')
		
		var accrualPeriodicity	= "N/A";
		var title				= "WRF Rainfall Accumulation"
		
		accrualPeriodicity 		= "R/P1D"
		title = req.gettext("products.wrf_precip_1d")
	
		
		
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
		                "fn": 		"Dalia Kirschbaum",
		                "hasEmail": "mailto:dalia.b.kirschbaum@nasa.gov"
		            },
		            "description": "This dataset provides WRF rainfall data",
		            "distribution": [
		                {
		                    "downloadURL": source_url,
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
		                "name": "MARN",
		                "subOrganizationOf": {
		                    "name": "Goddard Space Flight Center",
		                    "subOrganizationOf": {
		                        "name": "NASA"
		                    }
		                }
		            },
		            "title": 	title,
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

	//options.MultipleProductsPerDay = function(prefix) {
	//	debug("MultipleProductsPerDay", prefix)
	//	var arr = prefix.split(".")
	//	prefix 	= arr[0]
	//	
	//	if( prefix == "fct_precip_1d") {
	//		return true
	//	} else {
	//		return false
	//	}
	//}
	
	var query					= new Query(options)
    query.source				= "wrf_30km"
	
	module.exports.query		= query;
