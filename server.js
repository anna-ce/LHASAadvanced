/**
 * Module dependencies.
 */

var express 		= require('express'),
	path			= require('path'),
	util			= require('util'),
	fs				= require('fs'),
  	debug 			= require('debug')('server'),
	eyes			= require('eyes'),
	mkdirp			= require('mkdirp'),
	Hawk			= require('hawk'),
	
	home			= require('./app/controllers/home'),
	s3				= require('./app/controllers/s3'),
	test			= require('./app/controllers/test'),
	users			= require('./app/controllers/users'),
	stats			= require('./app/controllers/stats'),
	opensearch		= require('./app/controllers/opensearch'),
	persona			= require('./app/controllers/persona'),
	App				= require('./models/app'),
	User			= require('./models/user')
	apps			= require('./app/controllers/apps'),
	products		= require('./app/controllers/products');
	
var app = module.exports = express();

global.app 			= app;
app.root 			= process.cwd();

var mainEnv 		= app.root + '/config/environment'+'.js';
var supportEnv 		= app.root + '/config/environments/' + app.settings.env+'.js';

require(mainEnv)
require(supportEnv)

// load settings
require('./settings').boot(app)  

// load controllers
require('./lib/boot')(app, { verbose: !module.parent });
	
// make sure tmp subdirs exist
for( var r in app.config.regions) {
	var region = app.config.regions[r]
	var bucket = region['bucket']
	var subdir = path.join(app.root, "tmp", bucket)
	console.log("mkdirp:", subdir)
	mkdirp(subdir)
}

// =========================================
// ROUTING
//

// enable CORS
// DOES NOT SEEM TO WORK
//app.all('/', function(req, res, next) {
//	console.log("enable CORS")
//	res.header("Access-Control-Allow-Origin", "*");
//	res.header("Access-Control-Allow-Headers", "X-Requested-With");
//	next();
// });
 
function if_authorized(req, res, next) {
	//console.log("if_authorized headers", req.headers)
	//console.log("if_authorized session", req.session)
	
	//if (req.session.user()) { 
		return next();
	//}
	//logger.info("auth not authenticated... please login...")
	//res.redirect('/login')
}

function SendOAuthUnAuthorizedResponse( res, err ) {
	var headers = {
		'Status': "Unauthorized",
		"WWW-Authenticate": "Hawk"
	}
	res.send("Unauthorized", headers, 401)
}

// Check that app is registered with us
function FindCredentialsFunc(id, callback) {
	console.log("Checking credentials for", id)
	App.get_by_fbappid(id, function(err, data) {
		console.log("App.get_by_fbappid", err)
		if(!err) {
			var credential = {
				id: id,
				key: data.secret,
				algorithm: 'sha256',
			}
		    callback(null, credential);
		} else {
			console.log("Cannot find appid:", id)
		    callback(null, undefined);			
		}
	})
}

function SetSessionCredential( req, res, err, credentials, artifacts, next ) {
	console.log('hawk.server.authenticate', err)
	if( err ) {
		SendOAuthUnAuthorizedResponse(res, err)
	} else {
		req.session.credentials = credentials
		var email = artifacts.ext
		User.get_by_email(email, function(err, user) {
			if( !err ) {
				req.session.user = user
				console.log("hawk passed for ", email)
				next()
			} else {
				var md5 = crypto.createHash('md5').update(email + app.secret).digest("hex");

				var json = {
					singly_id: md5,
					md5: 	md5,
					email: 	email,
					gravatar: new_avatar(md5)
				}

				var user = new User(email, email, email, null, null, null, {});
				user.save(json, function(err, user) {
					if (!err) {
						req.session.user = user
						next()
					}
				})
			}
		})
	}
}

function hawk_restrict(req, res, next) {
	if( req.session.user ) return next()
	console.log("hawk_restrict client check...")
	Hawk.server.authenticate(req, FindCredentialsFunc, {}, function(err, credentials, artifacts) {
		SetSessionCredential( req, res, err, credentials, artifacts, next )
	})
}
// Home page -> app
app.get('/', 									home.index);
app.get('/about', 								home.about);
app.get('/contact', 							home.contact);
app.get('/privacy', 							home.privacy);
app.get('/terms',	 							home.terms);
app.get('/support', 							home.support);

//app.get('/login', 								login.index);
//app.get('/logout', 								login.logout);

//app.get('/users', 								users.index);
app.get('/users/:id',	 						users.show);
app.post('/users/:id',	 						users.update);
app.get('/users', 								users.list);

// compatibility for editor
app.get('/user/:name',	 						users.show_by_name);

app.get('/stats', 								stats.index);

app.get('/s3/:bucket/:id',						s3.index);

app.get('/test/:id', 							test.index);
app.get('/test',								test.index);

app.get('/opensearch',							if_authorized, opensearch.index);

app.all('/persona/verify',						persona.verify);
app.all('/persona/logout',						persona.logout);

//app.get('/social/facebook',						social.facebook);
//app.get('/social/twitter',						social.twitter);

app.get('/products/opensearch',					hawk_restrict, products.opensearch);
app.get('/products/:region/:ymd/:id.:fmt?',		products.distribute);
app.get('/products',							products.index);

// Applications
app.get('/apps',								hawk_restrict, apps.index);
app.post('/apps',								hawk_restrict, apps.create);
app.get('/apps/form',							hawk_restrict, apps.form);
app.get('/apps/:id',							hawk_restrict, apps.show);
app.get('/apps/edit/:id',						hawk_restrict, apps.edit);
app.get('/apps/delete/:id',						hawk_restrict, apps.delete);
app.put('/apps/:id',							hawk_restrict, apps.update);
app.delete('/apps/:id',							hawk_restrict, apps.delete);

//
// returned to OPTIONS
function setOptionsHeaders(req, res) {	
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Content-Type,Authorization");	
    res.header("Access-Control-Allow-Methods", "POST,GET,PUT");	
    res.header("Allow", "POST,GET,PUT");	
    //res.header("Content-Length", "0");	
    //res.header("Content-Type", "text/html; charset=utf-8");	
	res.send(200)
}

function setAuthHeaders(req, res, next) {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Authorization");
	next()
}

// ===========================================================
// port set based on NODE_ENV settings (production, development or test)
debug("trying to start on port:"+ app.get('port'));

if (!module.parent) {
	app.listen(app.get('port'));
	
	logger.info( "**** "+app.config.application+' started on port:'+app.get('port'));
}