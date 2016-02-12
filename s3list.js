var	aws				= require("aws-sdk")

var params = {
    Bucket: "ojo-global",
    Prefix: "gpm",
	MaxKeys: 2000
};

var s3DataContents = [];    // Single array of all combined S3 data.Contents

// AWS Amazon
s3_config = {
	accessKeyId: 		process.env.AWS_ACCESSKEYID, 
	secretAccessKey: 	process.env.AWS_SECRETACCESSKEY,
	region:				process.env.AWS_REGION || 'us-east-1'
}

aws.config.update(s3_config);
var s3 = new aws.S3();

function s3Print() {
	for (var i = 0; i < s3DataContents.length; i++) {
		console.log(s3DataContents[i].Key);
	}
	console.log("s3DataContents.length",s3DataContents.length)
}

function s3ListObjects(params, cb) {
    s3.listObjects(params, function(err, data) {
        if (err) {
            console.log("listS3Objects Error:", err);
        } else {
            var contents = data.Contents;
			
			console.log("S3 returned %s objects", contents.length)
			
            s3DataContents = s3DataContents.concat(contents);
            if (data.IsTruncated) {
                // Set Marker to last returned key
                params.Marker = contents[contents.length-1].Key;
				console.log("Truncated data.  lastKey: %s", JSON.stringify(params.Marker))
				
                s3ListObjects(params, cb);
            } else {
                cb();
            }
        }
    });
}

s3ListObjects(params, function() {
	s3Print()	
})