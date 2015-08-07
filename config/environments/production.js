var express = require('express'),
	fs 		= require('fs'),
	debug 	= require('debug')('settings');

//app.configure('production', function() {
//	debug("configure production");
//  	app.use(express.logger());
//  	app.use(express.errorHandler());
//  	app.enable('view cache');
//  	app.enable('model cache');
//  	app.enable('eval cache');
//  	app.settings.quiet = true;	
//});

	var tmpdir = "/app/tmp";
	app.set('tmp_dir', tmpdir)

	// make sure that the /app/tmp directory exists
	if( !fs.existsSync(tmpdir) ) {
		console.log("Creating tmp")
		fs.mkdir(tmpdir, function(err) { 
			console.log("Creating /app/tmp error:", error)
		});
	} else {
		console.log("tmpdir already exists")
	}

	app_port = process.env.PORT;
	app.set('port', app_port)
	