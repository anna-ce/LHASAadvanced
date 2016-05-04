var util 		= require('util'),
	fs			= require('fs'),
	async	 	= require('async'),
	path		= require('path'),
	moment		= require('moment'),
	_			= require('underscore'),
	Hawk		= require('hawk'),
	filesize 	= require('filesize'),
	Query		= require('./query_s3');
		
	var source_url 	= "http://forecast.io/"
	var icon	 	= "/img/coffee.png"
	
	var options = {
		//bucket: 		'ojo-workshop',
		subfolder: 		'forecastio',
		browse_img: 	'_thn.jpg',						// will be something like subfolder.yyyymmddxxxxx
		geojson: 		'.geojson',
		geojsongz: 		'.geojson.gz',
		topojson: 		undefined,
		topojson_gz: 	undefined,
		source: 		'sources.forecastio',
		sensor: 		'sensors.forecastio',
		resolution: 	'10m',
		original_url:   source_url,
		product: 		'forecastio',
		tags: 			['forecastio'],
		minzoom: 		6
	}

	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.forecastio.credits"),
			"url": 		source_url,
		};
		return json;
	}

	options.style = function(req) {
		var host 	= req.protocol + "://"+ req.get('Host')
		var iconUrl	= host + icon
		 
		var json = {
			"true": {
				'property': 		'dewPoint',
				'marker-symbol': 	'cafe',
				'marker-color': 	['#c35817','#ffa500','#00ff00' ],
				'limits': 			[62, 68],
				'marker-size': 		'small'
			}
		}
		return json
	}

	options.legend = function(req) {
		var host 	= req.protocol + "://"+ req.get('Host')
		var iconUrl	= host + icon
		
		var html = "<style id='quakes_legend_style' >"
	    html += ".quakes_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".quakes_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".quakes_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 16px;"
		html += "  border-radius: 8px;"
		html += "  	-webkit-border-radius: 8px;"
		html += "  	-moz-border-radius: 8px;"
			
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".quakes_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".quakes_map-info {"
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
	
		html += "<div id='quakes_legend' class='quakes_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.quakes.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><img src='"+iconUrl+"' width=32 />&nbsp;"+ req.gettext("legend.quakes.legend") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.quakes.source.label")+": <a href='" + source_url+"'>"+ req.gettext("legend.quakes.source.source")+"</a>"
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
		
		var product 			= options.product
		var legend				= "legend."+ options.product
		var product_description	= req.gettext(legend)
		var url					= req.url
		var host 				= req.protocol + "://"+ req.get('Host')
		
		var accrualPeriodicity	= "R/P1D";
		var title				= "Coffee Plantation Forecast"

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
		            "description": "This dataset provides point data from Coffee Plantations",
		            "distribution": [
		                {
		                    "downloadURL": "http://centroclima.org",
		                    "mediaType": "html"
		                }
		            ],
		            "identifier": url,
		            "keyword": [
		                "coffee",
		                "precipitation",
						'temperature'
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
		                "name": "CentroClima",
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
	
	var query				= new Query(options)
	query.source			= "forecastio"
	module.exports.query 	= query;


