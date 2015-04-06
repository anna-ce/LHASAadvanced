var util 			= require('util'),
	fs				= require('fs'),
	async	 		= require('async'),
	path			= require('path'),
	moment			= require('moment'),
	request			= require('request'),
	xml2js 			= require('xml2js'),
	_				= require('underscore'),
	mime			= require('mime-types'),
	Hawk			= require('hawk'),
	query_pop		= require("../lib/query_pop"),

	debug			= require('debug')('pop');
	
	var bbox 		= 	[60, 20, 80, 40]
	var centerlon	= (bbox[0]+bbox[2])/2
	var centerlat	= (bbox[1]+bbox[3])/2
	var target		= [centerlon, centerlat]
	
	function render_map(region, url, req, res) {
		debug("render_map", url)
		res.render("products/map_api", {
			region: region,
			url: url,
			layout: false
		})
	}
	
	module.exports = {

		browse: function(req,res) {
			var year 		= req.params['year']
			var doy 		= req.params['doy']
			var date 		= moment(year+"-"+doy)
			var host 		= "http://"+req.headers.host
			var subfolder	= req.params.subfolder
			var region		= app.config.regions[subfolder]
			var bucket		= region.bucket
			
			
			//var region 	= {
			//	name: 	req.gettext("legend.population_count.title"),
			//	scene: 	year+"-"+doy,
			//	bbox: 	bbox,
			//	target: target
			//}
			
			var jday	= date.dayOfYear()
			if( jday < 10 ) {
				jday = "00"+jday
			} else if( jday < 100 ) jday = "0"+jday

			var month = date.month() + 1
			if( month < 10 ) month = "0"+ month

			var day		= date.date();
			if( day < 10 ) day = "0"+day
			
			var s3host				= "https://s3.amazonaws.com/"+bucket+"/ls/2011/"
			var browse_img_url		= s3host+"ls.2011_thn.jpg"
			var topojson_url		= s3host+"ls.2011.topojson"
			var topojson_file		= s3host+"ls/2011.topojson.gz"
			
			res.render("products/pop", {
				social_envs: 	app.social_envs,
				description: 	req.gettext("legend.population_count.title") +" - "+date.format("YYYY-MM-DD"),
				image: 			browse_img_url,
				url: 			host+"/products/"+subfolder+"/browse/pop/"+year+"/"+doy,
				map_url: 		host+"/products/"+subfolder+"/map/pop/"+year+"/"+doy,
				date: 			date.format("YYYY-MM-DD"),
				region: 		region,
				data: 			"http://web.ornl.gov/sci/landscan/",
				topojson: 		topojson_file,
				layout: 		false
			})
		},

		map: function(req,res) {
			var year 		= req.params['year']
			var doy 		= req.params['doy']
			var date 		= moment(year+"-"+doy)
			var host 		= "http://"+req.headers.host
			var bbox		= bbox
			var id			= year+"-"+doy
			var subfolder	= req.params.subfolder
			var region		= app.config.regions[subfolder]
			var bucket		= region.bucket
			
			console.log("map", region.bbox)
			//var region 	= {
			//	name: 	req.gettext("legend.population_count.title")+" "+date.format(req.gettext("formats.date")),
			//	scene: 	id,
			//	bbox: 	undefined,	// feature.bbox,
			//	target: target,
			//	min_zoom: 6
			//}
			region.bbox = undefined
			var url = "/products/"+subfolder+"/query/pop/"+year+"/"+doy
			render_map(region, url, req, res )
		},
		
		query: function(req, res) {
			var year 		= req.params['year']
			var doy 		= req.params['doy']
			var regionKey	= req.params['subfolder']
			
			var user		= req.session.user
			var credentials	= req.session.credentials
			
			var entry = query_pop.QueryByID(req, user, year, doy, regionKey, credentials)
			res.send(entry)
		},
		
		process: function(req,res) {
	
		}
	};