var express = require('express'),
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

	app.set('tmp_dir', '/app/tmp')

	// make sure that the /app/tmp directory exists
	mkdirp('/app/tmp', function(err) { 
		console.log("Creating /app/tmp error:", error)
	});

	app_port = process.env.PORT;
	app.set('port', app_port)
	