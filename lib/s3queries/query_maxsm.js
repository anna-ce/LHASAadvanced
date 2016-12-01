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
	
	var options = {
		bucket: 		'ojo-global',
		subfolder: 		'maxsm',
		browse_img: 	"_thn.png",
		geojson: 		undefined,
		topojson: 		undefined,
		topojson_gz: 	".topojson.gz",
		source: 		'sources.ef5',
		sensor: 		'sensors.ef5',
		resolution: 	'400m',
		original_url:   'http://flash.ou.edu/',
		product: 		'maxsm',
		tags: 			['maxsm','flood', 'drought', 'hazard'],
		minzoom: 		6
	}

    var levels		= [ 1,2,3,5,8,13,21,34,55,89]
    var hexColors	= [ "#c0c0c0", "#018414","#018c4e","#02b331","#57d005","#b5e700","#f9f602","#fbc500","#FF9400","#FE0000"]
	var source_url	= "http://flash.ou.edu/"
	
	var text 		= [	]
	function build_text() {
		for( var l in levels ) {
			var legend_entry = "legend.maxsm.legend."+levels[l]
			text.push(legend_entry)
		}
	}
	build_text()
	
	options.credits	= function(req) {
		var json = {
			"credits":  req.gettext("legend.maxsm.credits"),
			"url": 		source_url,
		};
		return json;
	}

	var json_3hr 			= {}

	function build_json(json, levels) {
		for( var i in levels) {
			var level = levels[i]
			var hash  = "{maxsm}=="+level
			json[hash] = {
				color: hexColors[i], 	
				fillOpacity: 0.3,
				weight: 1
			}
			if( i == 0 ) json[hash].weight = 0
		}		
	}
	
	build_json(json_3hr, levels)
	
	options.style = function(req) {
		return json_3hr
	}

	options.legend = function(req) {
		
		var html = "<style id='maxsm_legend_style' >"
	    html += ".maxsm_map-info .legend-scale ul {"
	    html += "   margin: 0;"
	    html += "   margin-bottom: 5px;"
	    html += "   padding: 0;"
	    html += "   float: right;"
	    html += "   list-style: none;"
	    html += "   }"
		html += ".maxsm_map-info .legend-scale ul li {"
		html += "   font-size: 80%;"
		html += "   list-style: none;"
		html += "    margin-left: 0;"
		html += "    line-height: 18px;"
		html += "    margin-bottom: 2px;"
		html += "}"
	    html += ".maxsm_map-info ul.legend-labels li span {"
	    html += "  display: block;"
	    html += "  float: left;"
	    html += "  height: 16px;"
	    html += "  width: 30px;"
	    html += "  margin-right: 5px;"
	    html += "  margin-left: 0;"
	    html += "  border: 1px solid #999;"
	    html += "}"
	    html += ".maxsm_map-info .legend-source {"
	    html += "   font-size: 70%;"
	    html += "   color: #999;"
	    html += "   clear: both;"
	    html += "}"
		html += ".maxsm_map-info {"
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
	
		html += "<div id='maxsm_legend' class='maxsm_map-info'>"
		html += "  <div class='legend-title'>"+ req.gettext("legend.maxsm.title")+"</div>"
		html += "  <div class='legend-scale'>"
		html += "    <ul class='legend-labels'>"
		
		
		for( var i in hexColors) {
			var rev = hexColors.length -1 -i
			//console.log(text[rev], req.gettext(text[rev]))
			var t= "	   <li><span style='background: " + hexColors[rev] + "'></span>&nbsp;"+ req.gettext(text[rev]) +"</li>"
			html += t
		}
		
		html += "    </ul>"
		html += "  </div>"
		html += "<div class='legend-source'>"+ req.gettext("legend.maxsm.source.label")+": <a href='"+source_url+"'>"+ req.gettext("legend.maxsm.source.source")+"</a>"
		html += "</div>&nbsp;&nbsp;"
		
		return html
	}
	
	options.MultipleProductsPerDay = function(prefix) {
		return true
	}
	
	var query 				= new Query(options)
	query.source			= "ef5"
	module.exports.query	= query;
