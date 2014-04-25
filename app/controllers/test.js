var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var async		= require('async');
var request		= require('request');
var debug		= require('debug')('tests');

function getClientAddress(request){ 
    with(request)
        return (headers['x-forwarded-for'] || '').split(',')[0] 
            || connection.remoteAddress
}

// horrible to work around throttling of github
function sleep(milliseconds) {
  var start = new Date().getTime();
  for (var i = 0; i < 1e7; i++) {
    if ((new Date().getTime() - start) > milliseconds){
      break;
    }
  }
}

module.exports = {
	
	index2: function(req, res) {       
		var id 	= req.params['id'];
		var ip 	= getClientAddress(req)
		var url = 'http://freegeoip.net/json/' + ip
		request.get( url, function (error, response, body) {
			if(!error && response.statusCode == 200 ) {
				var data = JSON.parse(body)
				console.log(data)
			}
		})
		
		res.render("test/index.ejs", {layout: false})
	},
	
	index: function(req, res) {
		var userid = 2

		function getAuthorInfo( cb ) {
			sleep(1000)
			console.log("getAuthorInfo", userid)
			cb(null)
		}
		function updateModifiedRecords( cb ) {
			async.eachSeries([1,2,3,5,8], function(el, next) {
				console.log("Modifying", userid, el)
				sleep(1000)
			
				next(null)
			}, function(err) {
				console.log("updateModifiedRecords done")
				cb(null)
			})
		}
		function createChangeSet( cb ) {
			console.log("creating Changeset...")
			sleep(1000)
			console.log("created!")
			cb(null)
		}
				
		async.series([
			getAuthorInfo,
			updateModifiedRecords,
			createChangeSet
		], function(err, results) {
				if( err ) {
					console.log("** Err async series", err)
				} else {
					console.log("changeset saved")
				}
				res.send("Done")
			})
	}
};