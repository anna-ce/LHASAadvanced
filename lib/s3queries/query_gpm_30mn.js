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
	
	
	var source_url = "http://pmm.nasa.gov/"
	
	var options = {
		bucket: 		'ojo-*',
		subfolder: 		'gpm_30mn',					
		browse_img: 	"_thn.png",
		geojson: 		".geojson",
		topojson: 		undefined,
		topojson_gz: 	".topojson.gz",
		geotiff: 		".tif",
		source: 		'sources.gpm',
		sensor: 		'sensors.gpm',
		resolution: 	'0.1deg',
		original_url:   source_url,
		product: 		'precipitation',
		tags: 			['precip_30mn', 'precipitation', 'rainfall'],
		minzoom: 		6,
		attributes: [
			{
				"name": "precip",
				"type": "esriFieldTypeInteger"
			}
		],
		getvalue: 		function(val) { 
			var result = val/10;
			return result
		},
		prefix_map: 	{
			'precip_30mn': 	'gpm_30mn'
		}
	}
	
	var hexColors     		= [ "#c0c0c0", "#018414","#018c4e","#02b331","#57d005","#b5e700","#f9f602","#fbc500","#FF9400","#FE0000","#C80000","#8F0000"]
	var gpm_30mn_levels		= [ 1,2,3,5,10,20,40,70,120,200,350,600 ]
	
	var gpm_30mn_text 		= [ "legend.precipitation_gpm.legend.1",
								"legend.precipitation_gpm.legend.2",
								"legend.precipitation_gpm.legend.3",
								"legend.precipitation_gpm.legend.5",
								"legend.precipitation_gpm.legend.10",
								"legend.precipitation_gpm.legend.20",
								"legend.precipitation_gpm.legend.40",
								"legend.precipitation_gpm.legend.70",
								"legend.precipitation_gpm.legend.120",
								"legend.precipitation_gpm.legend.200",
								"legend.precipitation_gpm.legend.350",
								"legend.precipitation_gpm.legend.600"]
	
	var json_30mn 			= {}
	
	function build_json(json, levels) {
		for( var i in levels) {
			var level = levels[i]
			var hash  = "{precip}=="+level
			json[hash] = {
				color: hexColors[i], 	
				fillOpacity: 0.2,
				weight: 1
			}
			if( i == 0 ) json[hash].weight = 0
		}		
	}
	
	build_json(json_30mn, gpm_30mn_levels)
	
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
			},
		]

	options.subset_action 	= true
	options.esri 			= true
		
	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.precipitation_gpm.credits"),
			"url": 		source_url
		};
		return json;
	}
	
	options.style = function(req) {
		var product = req.query.product.split('.')[0]
		return json_30mn;
	}

	options.legend = function(req) {
		var product = req.query.product.split('.')[0]
		var text = gpm_30mn_text;
		
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
		html += "  <div class='legend-title'>"+ req.gettext("legend.precipitation_gpm.gpm_30mn")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		
		for( var i in hexColors) {
			var rev = hexColors.length -1 -i
			var t= "	   <li><span style='background: " + hexColors[rev] + "'></span>&nbsp;"+ req.gettext(text[rev]) +"</li>"
			html += t
		}
		
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.precipitation_gpm.source.label")+": <a href='"+source_url+"'>"+ req.gettext("legend.precipitation_gpm.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
	
		//console.log("legend title", req.gettext("legend.precipitation_gpm.title"))
	
		return html
	}
	
	options.tilejson = function(req) {
		var regionKey			= req.params['regionKey']
		var region				= app.config.regions[regionKey]
		var bucket				= region.bucket
		var year 				= req.params['year']
		var doy 				= req.params['doy']
		var prefix 				= req.params['prefix']
		
		var host				= req.protocol + "://"+ req.get('Host') 
		var url1 				= host + "/products/gpm_30mn/vt/Global/"+ year+"/" + doy+"/{z}/{x}/{y}/" + prefix+".mvt"
		
		var json = {
			"tilejson": 	"1.0.0",
			"name": 		"GPM/IMERG 30mn",
			"description": 	"GPM/IMERG accumulated precipitation for last 30mn",
			"version": 		"1.0.0",
			"attribution": 	"NASA/GSFC",
			"scheme": 		"xyz",
			"tiles": [
		        url1,
			],
			"minzoom": 		0,
			"maxzoom": 		18,
			"bounds": 		[-180,-60,180, 60]
		}
		return json
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
		
		var	accrualPeriodicity = "R/P30M"
		var	title = req.gettext("products.precip_30mn")
				
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
	
	
	options.MultipleProductsPerDay = function(prefix) {
		var arr = prefix.split(".")
		prefix 	= arr[0]
		
		if( prefix == "gpm_30mn") {
			return true
		} else {
			return false
		}
	}
	
	var query					= new Query(options)
    query.source				= "gpm"
	
	module.exports.query		= query;
