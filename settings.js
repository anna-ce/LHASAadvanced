var express 		= require('express'),
	util			= require('util'),
	partials 		= require('express-partials'),
	assert			= require('assert'),
	fs				= require('fs'),
	path			= require('path'),
	debug 			= require('debug')('server'),
	engines			= require('consolidate'),
	pg 				= require('pg'),
	PGStore 		= require('connect-pg'),
	ejs				= require('ejs'),
	crypto 			= require('crypto'),
	eyes			= require('eyes'),
	aws				= require("aws-sdk"),
	winston 		= require('winston'),
	facebook		= require('./lib/facebook'),
	GitHubApi 		= require("github"),
	shortid			= require('shortid');
	
	
  	require('winston-papertrail').Papertrail;

	global.logger = new winston.Logger({
		transports: [
			new (winston.transports.Console)(),

			new winston.transports.Papertrail({
				host: 'logs.papertrailapp.com',
				port: 12836,
				colorize: true
			})
		]
	});

	// shortid for database key management
	shortid.seed(20130311);
	app.shortid = shortid;

	// AWS Amazon
	app.s3_config = {
		accessKeyId: 		process.env.AWS_ACCESSKEYID, 
		secretAccessKey: 	process.env.AWS_SECRETACCESSKEY,
		region:				process.env.AWS_REGION || 'us-east-1',
		cache_dir: 			"./tmp",
	}

	assert( app.s3_config.accessKeyId, "Missing S3 accessKeyID env" )
	assert( app.s3_config.secretAccessKey, "Missing S3 secretAccessKey env")
	assert( app.s3_config.region, "Missing S3 region env" )

	aws.config.update(app.s3_config);

	app.s3 = new aws.S3();

	logger.info("Connected to S3...")

	// Pick a secret to secure your session storage
	app.sessionSecret = process.env.COOKIEHASH || 'OJO-BOT-PGC-2014-04';
	

	exports.boot = function(app){

		// The port that this express app will listen on
		debug("app_port:"+app_port)
		
		var port

		if( app.settings.env === 'development') {
			port 			= app_port;
		} else {
			port 			= app.config.PORT;		
		}
		app.set('port', port)
		
		bootApplication(app)
		
		var appId			= process.env.fbAppId
		var appSecret		= process.env.fbSecret
		assert(appId)
		assert(appSecret)
		
		app.config.fbAppId	= appId
		app.config.fbSecret	= appSecret
		
		app.facebook		= facebook.init(appId, appSecret)

		app.facebook.GenerateSecret(function(err, secret) {
			logger.info("Application Hawk Key:", err,secret)
			app.hawk_secret = secret
			app.hawk_id 	= appId
		})		
	}
	
// ===============================	
// Helper to set env in app global
//
function app_set_env( env_var ) {
	app[env_var] = process.env[env_var]
	assert( app[env_var], env_var + " env is missing")
}
	
// ===========================
// App settings and middleware
function bootApplication(app) {

	// load config
	app.config 	= JSON.parse(fs.readFileSync("./config/config.yaml"));
	
	// define a custom res.message() method
	// which stores messages in the session
	app.response.message = function(msg){
	  // reference `req.session` via the `this.req` reference
	  var sess = this.req.session;
	  // simply add the msg to an array for later
	  sess.messages = sess.messages || [];
	  sess.messages.push(msg);
	  return this;
	};
	
	// serve static files
	app.use(express.static(__dirname + '/public'));
	app.use(partials());

	app.set('views', __dirname + '/app/views')
	app.set('helpers', __dirname + '/app/helpers/')
   	app.set('view engine', 'ejs');
	app.engine('html', engines.ejs);
	
	app.set('view options', { layout: 'layout.ejs' })

	// cookieParser should be above session
	app.use(express.cookieParser(process.env.COOKIEHASH))

	// bodyParser should be above methodOverride
	// app.use(express.bodyParser())
	app.use(express.json());
	app.use(express.urlencoded());
	
	app.use(express.methodOverride())

	var conString 	= process.env.DATABASE_URL || "tcp://nodepg:password@localhost:5432/dk";
	logger.info("Connecting to db:", conString)
		
 	function pgConnect (callback) {
		pg.connect(conString, function (err, client, done) {			
			if (err) {
				logger.info(JSON.stringify(err));
			}
			if (client) {
				callback(client);
			}
			done()	// THIS IS CRITICAL TO RETURN CLIENT TO THE POOL.... GRRRR!
		});
    };	
		
	app.use(express.session({
		  secret: app.sessionSecret,
		  cookie: { maxAge: 1 * 360000}, //1 Hour*24 in milliseconds
		  store: new PGStore(pgConnect)
	}))

	app.client = new pg.Client(conString);
	app.client.connect(function(err) {
	  if(err) {
	    return logger.error('could not connect to postgres', err);
	  }
	  app.client.query('SELECT NOW() AS "theTime"', function(err, result) {
	    if(err) {
	      	logger.error('error running query', err);
	    } else {
	    	logger.info("startup time: " + result.rows[0].theTime);
		}
	  });
	});
	
	app.use(express.favicon())
		
	//app.use(express.csrf());
	app.use(function(req, res, next) {
		//res.locals.token = req.csrfToken();
		//console.log('csrf:', res.locals.token);
		next()
	});

	app.use(function(req, res, next) {
	  req.raw_post = '';
	  req.setEncoding('utf8');

	  req.on('data', function(chunk) { 
	    req.raw_post += chunk;
	  });

	  next();
	});
	
	// expose the "messages" local variable when views are rendered
	app.use(function(req, res, next){

	  var msgs = req.session.messages || [];

	  // expose "messages" local variable
	  res.locals.messages = msgs;

	  // expose "hasMessages"
	  res.locals.hasMessages = !! msgs.length;

	  /* This is equivalent:
	   res.locals({
	     messages: msgs,
	     hasMessages: !! msgs.length
	   });
	  */

	  // empty or "flush" the messages so they
	  // don't build up
	  req.session.messages = [];
	  next();
	});
	
	app.use(app.router)
	
	// Error Handling
	app.use(function(err, req, res, next){
	  // treat as 404
	  if (~err.message.indexOf('not found')) return next()

	  // log it
	  console.error(err.stack)

	  // error page
	  res.status(500).render('500', { layout: false })
	})

	// assume 404 since no middleware responded
	app.use(function(req, res, next){
	  res.status(404).render('404', { layout: false, url: req.originalUrl })
	})
	
	//app_set_env('SENDGRID_USER')
	//app_set_env('SENDGRID_KEY')	
	//app.sendgrid  = require('sendgrid')(app.SENDGRID_USER, app.SENDGRID_KEY);
}
