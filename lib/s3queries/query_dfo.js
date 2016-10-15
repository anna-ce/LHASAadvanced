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
	
	var	bbox		=	[-190, 60, 180, -60];				// lng,lat bottom left - top right
	var	centerlon	=  	(bbox[0]+bbox[2])/2;
	var	centerlat	=	(bbox[1]+bbox[3])/2;
	
	var source_url = "http://floodobservatory.colorado.edu"
	
	var options = {
		bucket: 		app.config.regions.Global.bucket,
		subfolder: 		'dfo',
		browse_img: 	"_thn.jpg",
		geojson: 		undefined,
		topojson: 		".topojson",
		topojson_gz: 	".topojson.gz",
		//shape_gz:  		".shp.gz",
		shape_zip: 		undefined,
		geotiff: 		".tif",
		source: 		'sources.dfo',
		sensor: 		'sensors.dfo',
		resolution: 	'14km',
		original_url:   source_url,
		product: 		'flood_map',
		tags: 			['flood_map', 'flood'],
		bbox: 			bbox,							// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		2,
		attributes: [
			{
				"name": "flood",
				"type": "esriFieldTypeInteger"
			}
		],
		getvalue: 		function(val) { 
			var result = val;
			return result
		}
	}
	
	options.exports =  [
			{ 
				'ext': 'geojson',
				'mediaType': "application/json"
			},
			{ 
				'ext': 'shp.zip',
				'mediaType': "application/zip"
			},
			{ 
				'ext': 'osm.bz2',
				'mediaType': "application/bzip2"
			},
		]

	options.subset_action 	= true
	options.esri 			= true

	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.flood_map.credits"),
			"url": 		source_url
		};
		return json;
	}
	options.style = function(req) {
		var json = {
			"{flood}==1": {
				color: '0xff0000', 
				fillOpacity: 0.8,	
				weight: 2
			}
		}
		return json
	}

	options.legend = function(req) {
		var html = "<style id='flood_map_legend_style' >"
	    html += ".flood_map_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".flood_map_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".flood_map_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".flood_map_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".flood_map_map-info {"
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
	
		html += "<div id='flood_map_legend' class='flood_map_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.flood_map.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><span style='background: 0xff0000'></span>&nbsp;"+ req.gettext("legend.flood_map.legend") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.flood_map.source.label")+": <a href='"+source_url+"'>"+ req.gettext("legend.flood_map.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
	
		//console.log("new legend title", req.gettext("legend.flood_map.title"))
	
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
		                "fn": "Dr Bob Brakkenridge",
		                "hasEmail": "mailto:robert.brakenridge@colorado.edu"
		            },
		            "description": "This dataset provides global flood mapping",
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
		                "name": "Dartmouth Flood Observatory",
		                "subOrganizationOf": {
		                    "name": "Dartmouth University"
		                }
		            },
		            "title": 	"Global Flood Mapping",
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
	
	function FindRegionKey(lat, lon) {
		console.log("Global Region")
		var r = 'Global'
		return r
	}
	
	var query					= new Query(options)
    query.source				= "dfo"
    query.FindRegionKey			= FindRegionKey
	module.exports.query		= query;
