var util 		= require('util');
var fs	 		= require('fs');
var path		= require('path');
var eyes		= require('eyes');
var https		= require('https');
var debug		= require('debug')('s3');
var request		= require('request');
var zlib 		= require('zlib');
var tar			= require('tar');
var async		= require('async');
var mkdirp		= require("mkdirp");
var debug		= require('debug')('s3');

//
// Get cached file and return json
//
function get_cached_data( filename, callback ) {
	var data = fs.readFile( filename, function(err, data) {
		var json = JSON.parse(data)
		callback( err, json )
	})
}

function endsWith(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1;
}

function copyFromS3(bucket, key, cb ) {
	var options = {
		Bucket: bucket, 
		Key: key
	};
	app.s3.getObject( options, function(err, data) {
		var tmp_dir = app.get("tmp_dir")
		if( !err ) {
			if( endsWith(key, "/") ) {
				return cb(null)
			}
			
			var fileName = path.join(tmp_dir, bucket, key)
			var dir		 = path.dirname(fileName)
			
			console.log("copyFromS3", bucket, key, dir, fileName)
			
			// make sure folder exists
			mkdirp.sync(dir)

			if( dir != fileName ) {
				console.log("Trying to copy", fileName)
			
				var out 		= fs.createWriteStream(fileName)	
				var buff 		= new Buffer(data.Body, "binary")
				var Readable 	= require('stream').Readable;
				var rs 			= new Readable;
				rs.push(buff)
				rs.push(null)
				rs.pipe(out)
			}
			
		} else {
			console.log("NOT Found it on S3", fname)
		}
		cb(err)
	})
}

function synchronizeFile( bucket, key, size, cb ) {
	var tmp_dir = app.get("tmp_dir")
	var fName	= path.join(tmp_dir, bucket, key)
	//console.log("Checking", fName)
	if( !fs.existsSync(fName) ) {
		if( fName.indexOf(".mbtiles") < 0 ) {
			console.log("**", fName, "does NOT exist")
			copyFromS3(bucket, key, cb ) 
		} else {
			cb(null)
		}
	} else {
		// could check file size as well
		var stats = fs.statSync(fName)
		if( !stats.isDirectory() && (stats.size != size) ){
			console.log("Different size - update", fName)
			copyFromS3(bucket, key, cb ) 			
		} else {
			cb(null)
		}
	}
}

function sync_bucket( bucket, marker ) {
	var options = {Bucket: bucket, Marker: marker};
	app.s3.listObjects(options, function(err, data) {
		if( !err ) {
			//console.log(data)
			async.eachSeries( data.Contents, function( el, cb) {
				synchronizeFile(bucket, el.Key, el.Size, cb)
			}, function(err) {
				console.log("synchronized done", err)
				if( data.IsTruncated ) syncBucket(bucket, data.NextMarker)
			})
		} else {
			logger.error(err)
		}
	})
}


module.exports = {

	index: function(req, res) {       
		var bucket 			= req.params['bucket'];
		var id 				= req.params['id'];
		var ifNoneMatch 	= req.headers['if-none-match']
		var lastModified 	= req.headers['last-modified']
	
		var fileName		= path.join(app.root,'tmp',bucket,id.replace(".tgz", ""))
		
		if( fs.existsSync( fileName )) {
			// return it
			console.log("Found file in cache...", fileName)
			get_cached_data(fileName, function(err, json ) {
				res.send(json)				
			})
			return;
		}
		
		console.log("File ", fileName, " does not exists... fetching it from s3...")
		
		var options = {Bucket: bucket, Key: id};
		if( ifNoneMatch ) 	options["IfNoneMatch"] 		= ifNoneMatch
		if( lastModified ) 	options["IfModifiedSince"] 	= lastModified
		
		app.s3.getObject( options, function(err, data) {
			if( !err ) {
				var out 		= fs.createWriteStream(fileName)	
				
				var buff 		= new Buffer(data.Body, "binary")
				var Readable 	= require('stream').Readable;
				var rs 			= new Readable;
				rs.push( buff )
				rs.push(null)
				
				rs.pipe(zlib.createGunzip())
					.pipe(tar.Parse())
					.pipe(out)
				
				get_cached_data(fileName, function(err, json ) {
					if( !err ) {
						res.send(json)				
					}
				})
			} else {
				logger.error( "S3 getObject bucket %s key %s Err", bucket, id, err )
				res.send(err.statusCode)
			}
		})
	},
	
	// sync up our buckets and tmp directory
	sync: function(req, res) {
		synchronize();
		res.send("Done");
	},
	
	synchronize: function() {
		sync_bucket('ojo-d3', "")
		sync_bucket('ojo-d2', "")	
		console.log("/tmp synchronized with S3")	
	}
};