// Activity Streams
// Pat Cappelaere
// Inspired by jasnell/activitystrea.ms v2 1.4?
var mime_type = require("mime-types")

function Action(name, type) {
	this['@type'] 			= type
	this['displayName']		= name
	this['using']			= []
}

function HttpGetActionItem(id, name, url, size, media_type) {
	var mediaType 		= media_type || mime_type.lookup(url)
	this["@type"] 		= "as:HttpRequest"
	this["method"] 		= "GET"
	this["@id"] 		= id
	this["mediaType"]	= mediaType
	this["url"] 		= url
	this["displayName"]	= name

	if(size) this.size 	= size
}

Action.prototype.addActionItem = function(a) {
	this.using.push(a)
	return this
}

Action.prototype.addActionItems = function(items) {
	this.using = items
	return this
}

Action.prototype.addHttpGet = function (id, name, url, size, media_type) {
	var a = new HttpGetActionItem(id, name, url, size, media_type) 
		
	this.using.push(a)
	return this
}

// define entry object
function Entry(id, type, name) {
	this['@id'] 		= id
	this['@type']		= type
	this['displayName']	= name
}

Entry.prototype.stringify = function() {
	return JSON.stringify(this,null,"\t")
}

function Image(url) {
	var mediaType	= mime_type.lookup(url)
	this.url 		= url
	this.mediaType 	= mediaType
	this.rel		= "browse"
}

Entry.prototype.addProperty = function(tag,name,value) {
	if (this.properties == undefined) { this.properties = {}}
	this.properties[tag] = {
		"@label": name,
		"@value": value
	}
	return this
}

Entry.prototype.addImage = function(url, type) {
	var img = new Image(url, type)
	if (this.image == undefined) { this.image = []}
	this.image.push(img)
	return this
}

Entry.prototype.addAction = function(a) {
	
	if (this.action == undefined) { this.action = []}
	this.action.push(a)
	return this
}

Entry.prototype.geometry_bbox = function(bbox) {
	this.geometry = {
		"type": "Polygon",
		"coordinates": [[
			[bbox[0], bbox[1]],
			[bbox[0], bbox[3]],
			[bbox[2], bbox[3]],
			[bbox[2], bbox[1]],
			[bbox[0], bbox[1]]
		]]
	}
	return this
}

module.exports = {
	entry: function(id, type, name) {
		return new Entry(id, type, name)
	},
	action: function(name, type) {
		return new Action(name, type)
	},
	httpGetActionItem: function(name, url, size) {
		return new HttpGetActionItem(name, url, size)
	}
}