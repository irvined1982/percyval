#!/usr/bin/env python
#  Copyright 2011 David Irvine
#
#  This file is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This file is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with This file.  If not, see <http://www.gnu.org/licenses/>.
#
#  $Rev: 178 $:
#  $Author: ubuntu $:
#  $Date: 2013-01-13 11:49:04 +0100 (Sun, 13 Jan 2013) $:
#
# An example of how to add a new case to the tool.
# Stores a cache of the details so it can be updated again later

import os
import urllib2
import json
import sys
try:
	server=sys.argv[1]
	caseName=sys.argv[2]
	caseDir=sys.argv[3]
	caseOwner=sys.argv[4]
	jobId=sys.argv[5]
except IndexError:
	print "Usage: addMonitor <url> <caseName> <caseDir> <caseOwner> <jobId>"
	sys.exit(1)

# case ID is stored in this file so it can be loaded later
cacheFile=os.path.join(caseDir,".monitorsCache")
# Try to open the cache file
try:
	cache=open(cacheFile, 'r')
	data=json.load(cache)
	cache.close()
	# Cache file has been loaded, this means the case exists
	# So just add the LSF job ID to the case, this avoids
	# having lots of cases with the same name.
	case=data['id']
	data={
			'name':'jobId',
			'value':jobId,
		}
	# Add the LSF Job ID to the case
	url="%s/%s/feature/LSF/option/add" % (server, case)
	jdata=json.dumps(data)
	urllib2.urlopen(url, jdata)
except urllib2.HTTPError, e:
	# Talking to the Server failed, so just dump the error message and give up
	print e.read()
except IOError :
	# Couldn't open the cache file, so create a new case
	url="%s/create" % server
	print ("No cache found, creating new case.")
	data={
		# Required name of the case, freeform text field,
		'name':  caseName,
		# Required username - nldir1/nlpveh/etc.
		'owner': caseOwner,
		# Array of features and options required.
		'features':  [
			{
				# STar CCM residual information
				'name':'StarCCMResidualMonitor'
			},
			{
				# Image Gallery searches sub folders for images
				'name':'ImageGallery'
			},
			{
				# Movie Gallery searches sub folders for webm movies 
				'name':'MovieGallery'
			},
			{
				# LSF feature shows LSF job information
				'name':'LSF',
				'options':[
					{
						# Requires at least one jobId to be set to pull
						# job information.
						'name':'jobId',
						'value':jobId,
					},
				],
			}
		],
		# Casedir option is used by almost all features.
		'options':[
			{'name':'caseDir', 'value':caseDir},
		]}
	jdata=json.dumps(data)
	try:
		# Try to create a new case
		d=urllib2.urlopen(url, jdata)
		cache=open(cacheFile, 'w')
		cache.write(d.read())
		cache.close()
	except urllib2.HTTPError, e:
		# Talking to the server failed, print the whole error
		print e.read()
