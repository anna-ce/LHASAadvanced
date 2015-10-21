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
		bucket: 		'ojo-workshop',
		subfolder: 		'trmm_24',
		browse_img: 	"_thn.jpg",
		geojson: 		undefined,
		topojson: 		".topojson",
		topojson_gz: 	".topojson.gz",
		//shape_gz: 		".shp.gz",
		shape_zip: 		".shp.zip",
		geotiff: 		".tif",
		source: 		'sources.trmm',
		sensor: 		'sensors.trmm',
		resolution: 	'0,25deg',
		original_url:   'http://trmm.gsfc.nasa.gov',
		product: 		'precipitation',
		tags: 			['precip_1d', 'daily_precipitation', 'precipitation', 'rain'],
		bbox: 			bbox,							// lng,lat bottom left - top right
		target: 		[centerlon, centerlat],
		minzoom: 		6,
		displayName: 	"trmm_1d",
		prefix_map: 	{
			'precip_1d': 'trmm_24'
		}
	}
	
	var colors = ["#f7fcf0","#e0f3db","#ccebc5","#a8ddb5","#7bccc4","#4eb3d3","#2b8cbe","#0868ac","#084081","#810F7C","#4D004A"	]
	
	//# http://hclwizard.org/hcl-color-scheme/
	//http://vis4.net/blog/posts/avoid-equidistant-hsv-colors/
	//http://tristen.ca/hcl-picker/#/hlc/11/1/2F1511/F0F46C
	//var colors = ["#F0F46C", "#B1E879", "#78D68B", "#4BC19B", "#34AAA4", "#3F90A1", 
	//			"#527692", "#5F5D7B", "#60455E", "#563140", "#452126","#2F1511"]
		
	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.precipitation_trmm.credits"),
			"url": 		"http://trmm.nasa.gov/",
		};
		return json;
	}
	options.style = function(req) {
		var json = {
			"{daily_precipitation}==1": {
				color: colors[0], 
				fillOpacity: 0,	
				weight: 0
			},
			"{daily_precipitation}==2": {
				color: colors[0], 	
				fillOpacity: 0,	
				weight: 2
			},
			"{daily_precipitation}==3": {
				color: colors[0], 	
				weight: 2
			},
			"{daily_precipitation}==5": {
				color: colors[1], 	
				weight: 2
			},
			"{daily_precipitation}==8": {
				color: colors[2], 	
				weight: 2
			},
			"{daily_precipitation}==13": {
				color: colors[3], 	
				weight: 2
			},
			"{daily_precipitation}==21": {
				color: colors[4], 	
				weight: 2
			},
			"{daily_precipitation}==34": {
				color: colors[5], 	
				weight: 2
			},
			"{daily_precipitation}==55": {
				color: colors[6], 	
				weight: 2
			},
			"{daily_precipitation}==89": {
				color: colors[7], 	
				weight: 2
			},
			"{daily_precipitation}==144": {
				color: colors[8], 	
				weight: 2
			},
			"{daily_precipitation}==233": {
				color: colors[9], 	
				weight: 2
			},
			"{daily_precipitation}==377": {
				color: colors[10], 	
				weight: 2
			}
		}
		return json
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
		html += "  <div class='legend-title'>"+ req.gettext("legend.precipitation_trmm.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		html += "	   <li><span style='background: " + colors[10] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.377mm") +"</li>"
		html += "	   <li><span style='background: " + colors[9] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.233mm") +"</li>"
		html += "	   <li><span style='background: " + colors[8] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.144mm") +"</li>"
		html += "	   <li><span style='background: " + colors[7] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.89mm") +"</li>"
		html += "	   <li><span style='background: " + colors[6] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.55mm") +"</li>"
		html += "	   <li><span style='background: " + colors[5] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.34mm") +"</li>"
		html += "	   <li><span style='background: " + colors[4] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.21mm") +"</li>"
		html += "	   <li><span style='background: " + colors[3] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.13mm") +"</li>"
		html += "	   <li><span style='background: " + colors[2] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.8mm") +"</li>"
		html += "	   <li><span style='background: " + colors[1] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.5mm") +"</li>"
		html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.3mm") +"</li>"
		//html += "	   <li><span style='background: " + colors[0] + "'></span>&nbsp;"+ req.gettext("legend.precipitation_trmm.legend.2mm") +"</li>"
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.precipitation_trmm.source.label")+": <a href='http://trmm.nasa.gov/'>"+ req.gettext("legend.precipitation_trmm.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
	
		//console.log("legend title", req.gettext("legend.precipitation_trmm.title"))
	
		return html
	}
	
	var query				= new Query(options)
	query.source			= "trmm"
	module.exports.query 	= query;
