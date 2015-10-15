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
	
	var options = {
		bucket: 		"ojo-*",
		subfolder: 		'landslide_nowcast',
		browse_img: 	"_thn.jpg",
		geojson: 		undefined,
		topojson: 		".topojson",
		topojson_gz: 	".topojson.gz",
		shape_gz: 		".shp.gz",
		source: 		'sources.dk',
		sensor: 		'sensors.dk',
		resolution: 	'400m',
		original_url:   'http://ojo-bot.herokuapp.com',
		product: 		'landslide_nowcast',
		tags: 			['landslide_nowcast','landslide','hazard', 'disaster'],
		bbox: 			bbox,											// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		6,
		attributes: [
			{
				"name": "landslide_nowcast",
				"type": "esriFieldTypeInteger"
			}
		]
	}

	//var colors = ["#ffeda0","#f03b20"	]
	var colors = ["#FFCC5F","#f03b20"	]

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
			"credits":  req.gettext("legend.landslide_nowcast.credits"),
			"url": 		"http://ojo-bot.herokuapp.com",
		};
		return json;
	}

	options.style = function(req) {
		var json = {
			"{landslide_nowcast}==1": {
				color: colors[0],
				fillOpacity: 0.6,
				weight: 2
			},
			"{landslide_nowcast}==2": {
				color: colors[1], 	
				fillOpacity: 0.6,
				weight: 2
			}
		}
		return json
	}

	options.legend = function(req) {
		var html = "<style id='landslide_nowcast_legend_style' >"
	    html += ".landslide_nowcast_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".landslide_nowcast_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".landslide_nowcast_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".landslide_nowcast_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".landslide_nowcast_map-info {"
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
	
		html += "<div id='landslide_nowcast_legend' class='landslide_nowcast_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.landslide_nowcast.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.landslide_nowcast.legend.level_1") +"</li>"
		html += "	   <li><span style='background: " + colors[1] + "'></span>&nbsp;"+ req.gettext("legend.landslide_nowcast.legend.level_2") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.landslide_nowcast.source.label")+": <a href='http://http://pmm.nasa.gov'>"+ req.gettext("legend.landslide_nowcast.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
	
		//console.log("legend title", req.gettext("legend.stream_flow.title"))
	
		return html
	}
	
	options.metadata = function(req) {
		var regionKey	= req.params['regionKey']
		var region		= app.config.regions[regionKey]
		var bucket		= region.bucket
		var year 		= req.params['year']
		var doy 		= req.params['doy']
		var prefix 		= req.params['prefix']
		
		var product 			= options.product
		var legend				= "legend."+ options.product
		var product_description	= req.gettext(legend)
		var url					= req.url
		var host 				= req.protocol + "://"+ req.get('Host')
		
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
		                "fn": "Dalia Kirschbaum",
		                "hasEmail": "mailto:dalia.b.kirschbaum@nasa.gov"
		            },
		            "description": "This dataset provides a Landslide Nowcast",
		            "distribution": [
		                {
		                    "downloadURL": "http://pmm.nasa.gov/data-access/downloads/gpm",
		                    "mediaType": "html"
		                }
		            ],
		            "identifier": url,
		            "keyword": [
		                "landslide",
		                "disasters"
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
		                "name": "Precipitation Measurement Missions",
		                "subOrganizationOf": {
		                    "name": "Goddard Space Flight Center",
		                    "subOrganizationOf": {
		                        "name": "NASA"
		                    }
		                }
		            },
		            "title": 	"Landslide Nowcast",
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
	
	var query				= new Query(options)
    query.source			= "landslide_model"
	module.exports.query	= query;
