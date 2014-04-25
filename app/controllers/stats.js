var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var debug		= require('debug')('tests');

// pull stats from segment_io / google analytics
// Mapbox for maps
// Papertrail for logs
// 

module.exports = {
	
	index: function(req, res) {       
		var user	= req.session.user
		var id 		= req.params['id'];
		res.render("stats/index.ejs", {user: user})
	}
};