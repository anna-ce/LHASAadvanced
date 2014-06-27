var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var async		= require('async');
var request		= require('request');
var debug		= require('debug')('mapinfo');
var dust		= require('dustjs-linkedin');

function get_eo1_legend() {
	var html = "<style id='eo1_legend_style' >"
	html += ".eo1_map-legend {"
	html += "	position: relative;"
	html += "	float: right;"
	html += "    line-height: 18px;"
	html += "    color: #555;"
	html += "}"
	html += ".eo1_map-legend i {"
	html += "    width: 32px;"
	html += "    height: 16px;"
	html += "    float: left;"
	html += "    margin-right: 5px;"
	html += "    opacity: 0.5;"
	html += "}"
	html += ".eo1_map-info {"
	html += "    padding: 6px 8px;"
	html += "   font: 14px/16px Arial, Helvetica, sans-serif;"
	html += "    background: white;"
	html += "    background: rgba(255,255,255,0.8);"
	html += "    box-shadow: 0 0 15px rgba(0,0,0,0.2);"
	html += "    border-radius: 5px;"
	html += "}"
	html += ".eo1_map-info h4 {"
	html += "    margin: 0 0 5px;"
	html += "    color: #777;"
	html += "}"
	html += "</style>"
	
	html += "<div id='eo1_legend' class='eo1_map-info eo1_map-legend'>"
	html += "	<i style='border-bottom:solid; color: #FF0000'></i>&nbsp;Water<br/>"
	html += "	<br/>"
	html += "	<a href='http://eo1.gsfc.nasa.gov/'>EO-1 Flood Map</a>"
	html += "</div>&nbsp;&nbsp;"
	return html
}

function get_trmm_24_legend() {
	var html = "<style id='daily_precipitation_legend_style' >"
	html += ".daily_precipitation_map-legend {"
	html += "	position: relative;"
	html += "	float: right;"
	html += "    line-height: 18px;"
	html += "    color: #555;"
	html += "}"
	html += ".daily_precipitation_map-legend i {"
	html += "    width: 32px;"
	html += "    height: 16px;"
	html += "    float: left;"
	html += "    margin-right: 5px;"
	html += "    opacity: 0.5;"
	html += "}"
	html += ".daily_precipitation_map-info {"
	html += "    padding: 6px 8px;"
	html += "   font: 14px/16px Arial, Helvetica, sans-serif;"
	html += "    background: white;"
	html += "    background: rgba(255,255,255,0.8);"
	html += "    box-shadow: 0 0 15px rgba(0,0,0,0.2);"
	html += "    border-radius: 5px;"
	html += "}"
	html += ".daily_precipitation_map-info h4 {"
	html += "    margin: 0 0 5px;"
	html += "    color: #777;"
	html += "}"
	html += "</style>"
	
	html += "<div id='daily_precipitation_legend' class='daily_precipitation_map-info daily_precipitation_map-legend'>"
	html += "	<i style='border-bottom:solid; color: #E0F3DB'></i>&nbsp;&nbsp;2<br/>"
	html += "	<i style='border-bottom:solid; color: #CCEBC5'></i>&nbsp;&nbsp;3<br/>"
	html += "	<i style='border-bottom:solid; color: #A8DDB5'></i>&nbsp;&nbsp;5<br/>"
	html += "	<i style='border-bottom:solid; color: #7BCCC4'></i>&nbsp;&nbsp;8<br/>"
	html += "	<i style='border-bottom:solid; color: #4EB3D3'></i>&nbsp;13<br/>"
	html += "	<i style='border-bottom:solid; color: #2B8CBE'></i>&nbsp;21<br/>"
	html += "	<i style='border-bottom:solid; color: #0868AC'></i>&nbsp;34<br/>"
	html += "	<i style='border-bottom:solid; color: #084081'></i>&nbsp;55<br/>"
	html += "	<i style='border-bottom:solid; color: #810F7C'></i>&nbsp;89<br/>"
	html += "	<i style='border-bottom:solid; color: #4D004B'></i>144<br/>"
	html += "	<br/>"
	html += "	<a href='http://trmm.gsfc.nasa.gov/'>TRMM 24hr Precip</a>"
	html += "</div>&nbsp;&nbsp;"
	return html
}

function get_wrf_24_legend() {
	var html = "<style id='daily_precipitation_24h_forecast_legend_style' >"
	html += ".daily_precipitation_24h_forecast_map-legend {"
	html += "	position: relative;"
	html += "	float: right;"
	html += "    line-height: 18px;"
	html += "    color: #555;"
	html += "}"
	html += ".daily_precipitation_24h_forecast_map-legend i {"
	html += "    width: 32px;"
	html += "    height: 16px;"
	html += "    float: left;"
	html += "    margin-right: 5px;"
	html += "    opacity: 0.5;"
	html += "}"
	html += ".daily_precipitation_24h_forecast_map-info {"
	html += "    padding: 6px 8px;"
	html += "   font: 14px/16px Arial, Helvetica, sans-serif;"
	html += "    background: white;"
	html += "    background: rgba(255,255,255,0.8);"
	html += "    box-shadow: 0 0 15px rgba(0,0,0,0.2);"
	html += "    border-radius: 5px;"
	html += "}"
	html += ".daily_precipitation_24h_forecast_map-info h4 {"
	html += "    margin: 0 0 5px;"
	html += "    color: #777;"
	html += "}"
	html += "</style>"
	
	html += "<div id='daily_precipitation_24h_forecast_legend' class='daily_precipitation_24h_forecast_map-info daily_precipitation_24h_forecast_map-legend'>"
	html += "	<i style='border-bottom:1px dotted #E0F3DB'></i>&nbsp;&nbsp;2<br/>"
	html += "	<i style='border-bottom:1px dotted #CCEBC5'></i>&nbsp;&nbsp;3<br/>"
	html += "	<i style='border-bottom:2px dotted #A8DDB5'></i>&nbsp;&nbsp;5<br/>"
	html += "	<i style='border-bottom:3px dotted #7BCCC4'></i>&nbsp;&nbsp;8<br/>"
	html += "	<i style='border-bottom:4px dotted #4EB3D3'></i>&nbsp;13<br/>"
	html += "	<i style='border-bottom:4px dotted #2B8CBE'></i>&nbsp;21<br/>"
	html += "	<i style='border-bottom:4px dotted #0868AC'></i>&nbsp;34<br/>"
	html += "	<i style='border-bottom:4px dotted #084081'></i>&nbsp;55<br/>"
	html += "	<i style='border-bottom:4px dotted #810F7C'></i>&nbsp;89<br/>"
	html += "	<i style='border-bottom:4px dotted #4D004B'></i>144<br/>"
	html += "	<br/>"
	html += "	<a href='http://wrf.msfc.nasa.gov/'>24hr Forecast Precip in mm</a>"
	html += "</div>&nbsp;&nbsp;"
	return html
}

function get_gfms_24_legend() {
	var html = "<style id='flood_nowcast_legend_style' >"
	html += ".flood_nowcast_map-legend {"
	html += "	position: relative;"
	html += "	float: right;"
	html += "    line-height: 18px;"
	html += "    color: #555;"
	html += "}"
	html += ".flood_nowcast_map-legend i {"
	html += "    width: 32px;"
	html += "    height: 16px;"
	html += "    float: left;"
	html += "    margin-right: 5px;"
	html += "    opacity: 0.5;"
	html += "}"
	html += ".flood_nowcast_map-info {"
	html += "    padding: 6px 8px;"
	html += "   font: 14px/16px Arial, Helvetica, sans-serif;"
	html += "    background: white;"
	html += "    background: rgba(255,255,255,0.8);"
	html += "    box-shadow: 0 0 15px rgba(0,0,0,0.2);"
	html += "    border-radius: 5px;"
	html += "}"
	html += ".flood_nowcast_map-info h4 {"
	html += "    margin: 0 0 5px;"
	html += "    color: #777;"
	html += "}"
	html += "</style>"
	
	html += "<div id='flood_nowcast_legend' class='flood_nowcast_map-info flood_nowcast_map-legend'>"
	html += "	<i style='border-bottom:4px dotted #FFA500'></i>&nbsp;&nbsp;Warning<br/>"
	html += "	<i style='border-bottom:4px dotted #FF0000'></i>&nbsp;&nbsp;Alert<br/>"
	html += "	<br/>"
	html += "	<a href='http://flood.umd.edu/'>Flood Nowcast</a>"
	html += "</div>&nbsp;&nbsp;"
	return html
}

function get_landslide_nowcast_legend() {
	var html = "<style id='landslide_nowcast_legend_style' >"
	html += ".landslide_nowcast_map-legend {"
	html += "	position: relative;"
	html += "	float: right;"
	html += "    line-height: 18px;"
	html += "    color: #555;"
	html += "}"
	html += ".landslide_nowcast_map-legend i {"
	html += "    width: 32px;"
	html += "    height: 16px;"
	html += "    float: left;"
	html += "    margin-right: 5px;"
	html += "    opacity: 0.5;"
	html += "}"
	html += ".landslide_nowcast_map-info {"
	html += "    padding: 6px 8px;"
	html += "   font: 14px/16px Arial, Helvetica, sans-serif;"
	html += "    background: white;"
	html += "    background: rgba(255,255,255,0.8);"
	html += "    box-shadow: 0 0 15px rgba(0,0,0,0.2);"
	html += "    border-radius: 5px;"
	html += "}"
	html += ".landslide_nowcast_map-info h4 {"
	html += "    margin: 0 0 5px;"
	html += "    color: #777;"
	html += "}"
	html += "</style>"
	
	html += "<div id='landslide_nowcast_legend' class='landslide_nowcast_map-info landslide_nowcast_map-legend'>"
	html += "	<i style='border-bottom:solid; color: #FFA500'></i>&nbsp;&nbsp;Caution</br>"
	html += "	<i style='border-bottom:solid; color: #FF0000'></i>&nbsp;&nbsp;Warning</br>"
	html += "	<br/>"
	html += "	<a href='http://gsfc.nasa.gov/'>Landslide Nowcast</a>"
	html += "</div>&nbsp;&nbsp;"
	return html
}

function get_landslide_nowcast_style() {
	// topojson object name
	var json = {
		"{forecast}==90": 	{
			color: "#FFA500", 
			weight:8
		},
		"{forecast}==99":	{
			color: "#FF0000", 
			weight:10
		}
	}
	return json
}

function get_trmm_24_style() {
	// topojson object name
	var json = {
		"{precip}==2": 	{
			color: "#F7FCF0", 
			weight:1
		},
		"{precip}==3":	{
			color: "#E0F3DB", 
			weight:1
		},
		"{precip}==5":	{
			color: "#CCEBC5", 
			weight:2
		},
		"{precip}==8":	{
			color: "#A8DDB5", 
			weight:3
		},
		"{precip}==13":	{
			color: "#7BCCC4", 
			weight:4
		},
		"{precip}==21":	{
			color: "#2B8CBE", 
			weight:4
		},
		"{precip}==34":	{
			color: "#0868AC", 
			weight:4
		},
		"{precip}==55":	{
			color: "#084081", 
			weight:4
		},
		"{precip}==89":	{
			color: "#810F7C", 
			weight:4
		},
		"{precip}>=144":	{
			color: "#4D004B", 
			weight:4
		}
	}
	return json
}

function get_wrf_24_style() {
	// topojson object name
	var json = {
		"{forecast}==2": 	{
			color: "#F7FCF0", 
			weight:1,
			dashArray: "10 5"
		},
		"{forecast}==3":	{
			color: "#E0F3DB", 
			weight:1,
			dashArray: "10 5"
		},
		"{forecast}==5":	{
			color: "#CCEBC5", 
			weight:2,
			dashArray: "10 5"
		},
		"{forecast}==8":	{
			color: "#A8DDB5", 
			weight:3,
			dashArray: "10 5"
		},
		"{forecast}==13":	{
			color: "#7BCCC4", 
			weight:4,
			dashArray: "10 5"
		},
		"{forecast}==21":	{
			color: "#2B8CBE", 
			weight:4,
			dashArray: "10 5"
		},
		"{forecast}==34":	{
			color: "#0868AC", 
			weight:4,
			dashArray: "10 5"
		},
		"{forecast}==55":	{
			color: "#084081", 
			weight:4,
			dashArray: "10 5"
		},
		"{forecast}==89":	{
			color: "#810F7C", 
			weight:4,
			dashArray: "10 5"
		},
		"{forecast}>=144":	{
			color: "#4D004B", 
			weight:4,
			dashArray: "10 5"
		}
	}
	return json
}

function get_gfms_24_style() {
	var json = {
		"{risk}==100": 	{
			color: "#FFA500", 
			weight: 3,
			dashArray: "10 5"
		},
		"{risk}>=200":	{
			color: "#FF0000", 
			weight: 3,
			dashArray: "10 5"
		}
	}
	return json
}

function get_eo1_style() {
	var json = {
		"true": {
			color: "#FF0000", 
			weight: 3
		}
	}
	return json
}


// ===================================================
// CREDITS
// ====================================================
function get_trmm_24_credits() {
	var json = {
		"credits":  "NASA GSFC",
		"url": 		"http://trmm.gsfc.nasa.gov/",
	};
	return json;
}

function get_landslide_nowcast_credits() {
	var json = {
		"credits":  "NASA GSFC",
		"url": 		"http://trmm.gsfc.nasa.gov/publications_dir/potential_landslide.html",
	};
	return json;
}

function get_wrf_24_credits() {
	var json = {
		"credits":  "NASA MSFC WRF",
		"url": 		"http://msfc.nasa.gov/",
	};
	return json;
}

function get_gfms_24_credits() {
	var json = {
		"credits":  "UMD GFMS",
		"url": 		"http://flood.umd.edu/",
	};
	return json;
}

function get_eo1_credits() {
	var json = {
		"credits":  "EO-1 GSFC",
		"url": 		"http://eo1.gsfc.nasa.gov/",
	};
	return json;
}

module.exports = {
	
	trmm_24: function(req, res) {
		var style 	= get_trmm_24_style();
		var html  	= get_trmm_24_legend();
		var credits = get_trmm_24_credits();
		res.render("mapinfo/trmm_24", { style: style, html: html, credits: credits })
	},
	
	trmm_24_style: function(req, res) {
		var json = get_trmm_24_style()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(json)
	},
	trmm_24_legend: function(req, res) {
		var html = get_trmm_24_legend()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'text/html');		
		res.send(html)
	},
	trmm_24_credits: function(req, res) {
		var str = get_trmm_24_credits()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	},
	
	wrf_24: function(req, res) {
		var style 	= get_wrf_24_style();
		var html  	= get_wrf_24_legend();
		var credits = get_wrf_24_credits();
		res.render("mapinfo/wrf_24", { style: style, html: html, credits: credits })
	},
	wrf_24_style: function(req, res) {
		var json = get_wrf_24_style()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(json)
	},
	wrf_24_legend: function(req, res) {
		var html = get_wrf_24_legend()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'text/html');		
		res.send(html)
	},
	wrf_24_credits: function(req, res) {
		var str = get_wrf_24_credits()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	},
	
	gfms_24: function(req, res) {
		var style 	= get_gfms_24_style();
		var html  	= get_gfms_24_legend();
		var credits = get_gfms_24_credits();
		res.render("mapinfo/gfms_24", { style: style, html: html, credits: credits })
	},
	gfms_24_style: function(req, res) {
		var json = get_gfms_24_style()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(json)
	},
	gfms_24_legend: function(req, res) {
		var html = get_gfms_24_legend()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'text/html');		
		res.send(html)
	},
	gfms_24_credits: function(req, res) {
		var str = get_gfms_24_credits()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	},
	
	eo1: function(req, res) {
		var style 	= get_eo1_style();
		var html  	= get_eo1_legend();
		var credits = get_eo1_credits();
		res.render("mapinfo/eo1", { style: style, html: html, credits: credits })
	},
	eo1_style: function(req, res) {
		var json = get_eo1_style()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(json)
	},
	eo1_legend: function(req, res) {
		var html = get_eo1_legend()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'text/html');		
		res.send(html)
	},
	eo1_credits: function(req, res) {
		var str = get_eo1_credits()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	},
	landslide_nowcast: function(req, res) {
		var style 	= get_landslide_nowcast_style();
		var html  	= get_landslide_nowcast_legend();
		var credits = get_landslide_nowcast_credits();
		res.render("mapinfo/landslide_nowcast", { style: style, html: html, credits: credits })
	},
	landslide_nowcast_style: function(req, res) {
		var json = get_landslide_nowcast_style()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(json)
	},
	landslide_nowcast_legend: function(req, res) {
		var html = get_landslide_nowcast_legend()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'text/html');		
		res.send(html)
	},
	landslide_nowcast_credits: function(req, res) {
		var str = get_landslide_nowcast_credits()
	    res.header("Access-Control-Allow-Origin", "*");
		res.set('Content-Type', 'application/json');		
		res.send(str)
	}
}