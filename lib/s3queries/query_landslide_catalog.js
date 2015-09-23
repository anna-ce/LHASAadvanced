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
	
	var	bbox		=	[-180, -90, 180, 90];				// lng,lat bottom left - top right
	var	centerlon	=  	(bbox[0]+bbox[2])/2;
	var	centerlat	=	(bbox[1]+bbox[3])/2;
	
	var options = {
		bucket: 		undefined,
		subfolder: 		'landslide_catalog',
		browse_img: 	"/img/landslide_catalog.png",
		geojson: 		undefined,
		topojson: 		undefined,
		topojson_gz: 	undefined,
		shape_gz: 		undefined,
		source: 		'sources.dk',
		sensor: 		'sensors.dk',
		resolution: 	'400m',
		original_url:   'http://ojo-streamer.herokuapp.com',
		product: 		'landslide_catalog',
		tags: 			['landslide_catalog','landslide','hazard', 'disaster'],
		bbox: 			bbox,											// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		6,
		attributes: [
			{
				"name": "landslide_catalog",
				"type": "esriFieldTypeInteger"
			}
		]
	}

	var fieldnames = {
		"0": 	"id",
		"1": 	"date",
		"2": 	"trigger",
		"3": 	"fatalities",
		"4": 	"location_accuracy",
		"5": 	"landslide_size",
		"6": 	"storm_name",
		"7": 	"landslide_type"
	}
	
	// generate geojson from database
	options.GetGeoJSON = function(cb) {
		//console.log("landslide catalog GetGeoJSON...")
		var fields = _.values(fieldnames)		
		var query 	= "SELECT "+ fields.join(',') +",way, ST_AsGeoJSON(ST_TRANSFORM(way,4326),4,0) from planet_osm_point"
		app.client.query(query, function(err, result) {
			var json = { 
				type: 'FeatureCollection',
				fieldnames: fieldnames,
				features: []
			}
		
			var propnames = _.invert(fieldnames)
			
			if( err ) {
				logger.error(query, err)
			} else {
				if( result && result.rows != undefined ) {
					//eyes.inspect(result.rows)
					for( var r in result.rows ) {
						var row 	= result.rows[r]				
						var feature = { 
							type: "Feature",
							properties: { },
							//properties: { id: parseInt(row.id) },
							geometry: JSON.parse(row.st_asgeojson)
						}
						delete row.st_asgeojson
						delete row.way
						
						//for( var e in row ){
						//	var key = propnames[e]
						//	feature.properties[key] = row[e]
						//}
						
						for( var e in row ) {
							feature.properties[e] = row[e]
						}
					
						//var dt = moment(row.tstamp)					
						//feature.properties['user_id'] 		= row.user_id
						//feature.properties['tstamp'] 			= dt.format('YYYY-MM-DD') //row.tstamp.toString()
						//feature.properties['version'] 		= row.version
						//feature.properties['changeset_id'] 	= row.changeset_id
					
						json.features.push(feature)
					}
				}
			}
			//console.log("GetGeoJSON", JSON.stringify(json.features[0]))
			cb(err,json)
		})
	}
	
	//var colors = ["#ffeda0","#f03b20"	]
	var colors = ["#FFCC5F","#f03b20"	]

	options.exports =  [
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

	// http://mw1.google.com/crisisresponse/icons/un-ocha/index.html#cat_disaster
	options.style = function(req) {
		var host = req.protocol + "://"+ req.get('Host')
		
		var json = {
			"true": {
				//property: 'brightness',
				//scale: 0.02,
				//fillOpacity: 0.5,
				weight: 0.5,
				color: '#ff0000',
				icon: host + "/img/disaster_landslide_32px_icon_bluebox.png",
				iconSize: [16,16],
				iconAnchor:[8,8]
			}
		}
		return json
	}

	options.legend = function(req) {
		var host 	= req.protocol + "://"+ req.get('Host')
		var iconUrl = host + "/img/disaster_landslide_32px_icon_bluebox.png"
		
		var html = "<style id='landslide_catalog_legend_style' >"
	    html += ".landslide_catalog_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".landslide_catalog_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".landslide_catalog_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".landslide_catalog_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".landslide_catalog_map-info {"
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
	
		html += "<div id='landslide_catalog_legend' class='landslide_catalog_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.landslide_catalog.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><img src='"+iconUrl+"' width=32 />&nbsp;"+ req.gettext("legend.landslide_catalog.legend") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.landslide_catalog.source.label")+": <a href='http://ojo-streamer.herokuapp.com'>"+ req.gettext("legend.landslide_catalog.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
		
	
		return html
	}
	
	options.metadata = function(req) {
		var regionKey	= "Global"
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
		            "description": "This dataset provides access to the current NASA GSFC Landslide Catalog",
		            "distribution": [
		                {
		                    "downloadURL": "http://pmm.nasa.gov/data-access/downloads/gpm",
		                    "mediaType": "html"
		                }
		            ],
		            "identifier": url,
		            "keyword": [
		                "landslide",
						"catalog",
		                "disasters"
		            ],
					"landingPage": "http://ojo-streamer.herokuapp.com",
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
		            "title": 	"Landslide Catalog",
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

	options.entry = function(req) {
		var host = req.protocol + "://"+ req.get('Host')
		
		var result = {
		"@id": 			"landslide_catalog",
		"@type": 		"geoss:landslide_catalog",
		"displayName": 	"landslide_catalog",
		"image": 		[ 
							{
								"url": host+"/img/landslide_catalog.png",
								"mediaType": "image/png",
								"rel": "browse"
							}
						],
		"properties": 	{
				"source": {
					"@label": req.gettext("properties.source"),
					"@value": "Dalia Kirschbaum"
				},
				"url": {
					"@label": req.gettext("properties.url"),
					"@value": "http://ojo-streamer.herokuapp.com"
				},
				"date": {
					"@label": req.gettext("properties.date"),
					"@value": moment().format(req.gettext("formats.date"))
				},
			},
		"geometry": {
			"type": "Polygon",
			"coordinates": [[
				[-180, -90],
				[-180,  90],
				[ 180,  90],
				[ 180, -90],
				[-180, -90]
			]]
		},
		"action": 	[
			{ 
				"@type": 			"ojo:browse",
				"displayName": 		req.gettext("actions.browse"),
				"using": [{
					"@type": 		"as:HttpRequest",
					"method": 		"GET",					
					"url": 			host+"/products/landslide_catalog/browse/Global/-/-/landslide_catalog",
					"mediaType": 	"html"
				}]
			},
			{
				"@type": 			"ojo:download",
				"displayName": 		req.gettext("actions.download"),
				"using": [{
					"@type": 		"as:HttpRequest",
					"method": 		"GET",
					"url": 			host+"/products/s3/Global/landslide_catalog/-/-/landslide_catalog.geojson",
					"mediaType": 	"application/json"
				}]
			},
			{
				"@type": 			"ojo:map",
				"displayName": 		req.gettext("actions.map"),
				"using": [
					{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"@id": 			"legend",
						"url": 			host+"/mapinfo/"+options.subfolder+"/legend",
						"mediaType": 	"text/html",
						"displayName": 	req.gettext("mapinfo.legend")
					},
					{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"@id": 			"style",
						"url": 			host+"/mapinfo/"+options.subfolder+"/style",
						"mediaType": 	"application/json",
						"displayName": 	req.gettext("mapinfo.style")
					},
					{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"@id": 			"credits",
						"url": 			host+"/mapinfo/"+options.subfolder+"/credits",
						"mediaType": 	"application/json",
						"displayName": 	req.gettext("mapinfo.credits")
					}
				]
			},
			{
				"@type": 			"ojo:metadata",
				"displayName": 		req.gettext("actions.metadata"),
				"using": [{
					"@type": 		"as:HttpRequest",
					"method": 		"GET",
					"url": 			host+"/products/"+ options.subfolder+"/metadata/Global/-/-/landslide_catalog",
					"mediaType": 	"application/json"
				}]
			},
			{
				"@type": 			"ojo:esri",
				"displayName": 		req.gettext("actions.esri"),
				"using": 			[{
					"@type": 		"as:HttpRequest",
					"method": 		"GET",
					"url": 			host+"/products/landslide_catalog/features/Global/-/-/landslide_catalog.geojson",
					"mediaType": 	"application/json"
				}]
			},
			{
				"@type": 			"ojo:export",
				"displayName": 		req.gettext("actions.export"),
				"using": 			[
					{
						"@type": 		"as:HttpRequest",
						"method": 		"GET",
						"url": 			host+"/products/landslide_catalog/export/Global/-/-/landslide_catalog.shp.zip",
						"displayName": 	'shp.zip',
						"mediaType": 	"application/zip"
					}
				]
			}
		]}
		return result
	}
	
	function FindRegionKey(lat, lon) {
		console.log("Global Region")
		var r = 'Global'
		return r
	}
	
	var query				= new Query(options)
    query.source			= "dk"
    query.FindRegionKey		= FindRegionKey
	
	module.exports.query	= query;
