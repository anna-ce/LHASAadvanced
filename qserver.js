//
// Minimum AWS Queue Server
//

// Load the http module to create an http server.
var http 		= require('http'),
	Consumer 	= require('sqs-consumer'),
	assert		= require('assert'),
	path		= require('path'),
	fs			= require('fs'),
	exec 		= require('child_process').exec,
	execFile	= require('child_process').execFile,
	spawn 		= require('child_process').spawn,
	fork 		= require('child_process').fork,
	AWS			= require("aws-sdk");

assert(process.env.AWS_ACCESSKEYID)
assert(process.env.AWS_SECRETACCESSKEY)
assert(process.env.AWS_REGION)
assert(process.env.AWS_QUEUE_URL)
	
// AWS Amazon
var s3_config = {
	accessKeyId: 		process.env.AWS_ACCESSKEYID, 
	secretAccessKey: 	process.env.AWS_SECRETACCESSKEY,
	region:				process.env.AWS_REGION || 'us-east-1'
}

AWS.config.update(s3_config);

var appRoot 			= process.cwd();

var sqs_consumer = Consumer.create({
	queueUrl: process.env.AWS_QUEUE_URL,
	handleMessage: function (message, done) {
		console.log("got sqs message", message.Body)
		// Let's try to find a script of that name
		var scriptName = path.join(appRoot, "python", message.Body+".sh")
		if( fs.existsSync(scriptName)) {
			console.log("Executing", scriptName)
			var cmd = "sh "+scriptName
			var python_process = exec(cmd) 
			python_process.stdout.on('data', function(data) {
			    process.stdout.write(data); 
			});
			python_process.stderr.on('data', function(data) {
			    process.stdout.write(data); 
			});
		} else {
			console.log("Script did not exist", scriptName)
		}
		done();
	},
  	sqs: new AWS.SQS()
});

sqs_consumer.on('error', function (err) {
  console.log(err.message);
});

sqs_consumer.start();

// Configure our HTTP server to respond with Hello World to all requests.
var server = http.createServer(function (request, response) {
  response.writeHead(200, {"Content-Type": "text/plain"});
  response.end("Hello World\n");
});

// Listen on port
var port = process.env.PORT
server.listen(port);

// Put a friendly message on the terminal
console.log("DATA_DIR", process.env.DATA_DIR)
console.log("worker running at", port);