var express = require('express'),
	debug 	= require('debug')('settings');

app.configure('development', function() {
	debug("configure development");
  	//app.use(express.logger('dev'));
  	//app.use(express.errorHandler({ dumpExceptions: true, showStack: true }));
});


app_port= process.env.PORT || 7465;;