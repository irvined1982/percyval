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
import json
import mimetypes
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import Http404
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from percyval.models import *


@csrf_exempt
def caseCreate(request):
	## Creates a new case in the database using the JSON data
	#  supplied by the end user.
	# Only create the case using json data, if there is no
	# json data, raise 400
	if request.method != 'POST':
		return HttpResponseBadRequest("No POST data received.")
	try:
		m=json.load(request)
	except:
		return HttpResponseBadRequest("Could not parse json data.")
	ALLOWED_FEATURES=['StarCCMResidualMonitor','ImageGallery','lsf']
	NEEDED_FIELDS=['features','owner','name']

	# Check for required fields
	for field in NEEDED_FIELDS:
		if field not in m:
			return HttpResponseBadRequest("Required field: %s not specified in JSON data." % field)
	# check options are valid for case
	if 'options' in m:
		for option in m['options']:
			if 'name' not in option:
				return HttpResponseBadRequest("option name not specified in JSON data." )
			if 'value' not in option:
				return HttpResponseBadRequest("option value not specified in JSON data." )
	# check features are valid
	for feature in m['features']:
		if 'name' not in feature:
			return HttpResponseBadRequest("Feature name not specified in JSON data.")
		if feature['name'] not in ALLOWED_FEATURES:
			return HttpResponseBadRequest("Invalid Feature Name: %s" % feature)
		# check options for features are valid
		if 'options' in feature:
			for option in feature['options']:
				if 'name' not in option:
					return HttpResponseBadRequest("option name not specified in JSON data." )
				if 'value' not in option:
					return HttpResponseBadRequest("option value not  specified in JSON data.")
	try:
		user = User.objects.get(username=m['owner'])
	except ObjectDoesNotExist:
		return HttpResponseBadRequest("Invalid owner name: %s" % m['owner'])
		
	# Create the case.
	c=Case.objects.create(name=m['name'], owner=user)
	try:
		# add the options
		for option in m['options']:
			c.options.create(
				name=option['name'],
				value=option['value'],
				)
	except KeyError:
		# don't worry if no options specified
		pass

	for feature in m['features']:
		(f, created)=c.features.get_or_create(name=feature['name'])
		if not created:
			try:
				# add options for feature
				for option in feature['options']:
					f.options.create(
						name=option['name'],
						value=option['value'],
						)
			except KeyError:
				# don't worry if not specified
				pass

	# Create a json object to return the id and name to the user
	data={
			'name':c.name,
			'id':c.id,
			}
	# spit it out.
	return HttpResponse(json.dumps(data),content_type="application/json")

## Deletes a case.
@login_required
def caseDelete(request, caseId):
	case=get_object_or_404(Case,pk=caseId)
	case.delete()
	return redirect(reverse("ListView.as_view(model=Case)"))

## Presents a confirmation screen, used only via the web gui.
@login_required
def confirmCaseDelete(request, caseId):
	case=get_object_or_404(Case,pk=caseId)
	return render_to_response('percyval/deleteCase.html',{'case':case},context_instance=RequestContext(request))

## Adds an option to an existing case.
def caseOptionAdd(request,caseId):
	raise NotImplementedError

## Overwrites an option for an existing case
def caseOptionSet(request,caseId):
	raise NotImplementedError

## Deletes an option from an existing case
def caseOptionDelete(request,caseId):
	raise NotImplementedError

## Adds a feature to an existing case.
@csrf_exempt
def caseFeatureAdd(request,caseId,feature):
	f=get_object_or_404(CaseFeature, name=feature,case__pk=caseId)
	if request.method != 'POST':
		return HttpResponseBadRequest("No POST data received.")
	try:
		m=json.load(request)
	except:
		return HttpResponseBadRequest("Could not parse json data.")
	if not 'name' in m:
		return HttpResponseBadRequest("option needs a name")
	if not 'name' in m:
		return HttpResponseBadRequest("option needs a value")
	f.options.create(name=m['name'],value=m['value'])
	data={
		'name':f.name,
		'id':f.id,
		}
	return HttpResponse(json.dumps(data),content_type="application/json")


## Deletes a feature from an existing case.
def caseFeatureDelete(request,caseId,feature):
	pass

## Adds an option to an existing feature.
def caseFeatureOptionAdd(request, caseId, feature):
	pass

## Sets an option for an existing feature.
def caseFeatureOptionSet(request, caseId, feature):
	pass

## Deletes an option from an existing feature.
def caseFeatureOptionDelete(request, caseId, feature):
	pass

def caseDefaultView(request, caseId):
	case=get_object_or_404(Case,pk=caseId)
	return render_to_response('percyval/case_detail.html',{'object':case,},context_instance=RequestContext(request))


############## Movie Gallery Feature Views ################

## Displays a list of movies available for the MovieGallery feature
def movieList(request,id):
	feature=get_object_or_404(CaseFeature, case__pk=id, name='MovieGallery')
	return render_to_response('percyval/features/movies/movieList.html',{'feature':feature, 'movies':feature.getMovies()},context_instance=RequestContext(request))

## Downloads a movie to the client for the MovieGallery feature.
def movieView(request,id,movie):
	feature=get_object_or_404(CaseFeature, case__pk=id, name='MovieGallery')
	path=feature.getMoviePath(movie)
	print mimetypes.guess_type(path)[0]
	response=HttpResponse(FileWrapper(open(path)), content_type=mimetypes.guess_type(path)[0])
	response['Content-Length']=os.path.getsize(path)
	return response

############## Web GL Scene Feature Views #################
def sceneList(request,id):
	feature.getSceneList()
	feature=get_object_or_404(CaseFeature, case__pk=id, name='WebGLScenes')
	return render_to_response('percyval/features/scenes/sceneList.html',{'feature':feature},context_instance=RequestContext(request))


############## Image Gallery Feature Views ################

## Displays a list of image galleries available for the ImageGallery feature.
def imageGalleryList(request,id):
	feature=get_object_or_404(CaseFeature, case__pk=id, name='ImageGallery')
	return render_to_response('percyval/features/images/imageGalleryList.html',{'feature':feature},context_instance=RequestContext(request))

## Displays an individual image gallery for the ImageGallery feature.
def imageGalleryView(request,id,gallery):
	feature=get_object_or_404(CaseFeature, case__pk=id, name='ImageGallery')
	allImages=feature.getImages()
	if not gallery in allImages:
		raise Http404
	images=allImages[gallery].values()
	images=sorted(images, key=lambda k: k['mTime'], reverse=True) 
	return render_to_response('percyval/features/images/imageGalleryView.html',{'feature':feature,'name':gallery,'images':images},context_instance=RequestContext(request))

## Downloads an image from an image gallery for the ImageGallery feature.
def imageView(request,id, image):
	feature=get_object_or_404(CaseFeature, case__pk=id, name='ImageGallery')
	path=feature.getImagePath(image)
	response=HttpResponse(FileWrapper(open(path)), content_type=mimetypes.guess_type(path)[0])
	response['Content-Length']=os.path.getsize(path)
	return response


############## Plotting Feature Views ################

# Returns a JSON object containing the data between the requested timesteps that FLOT can use
# to render the graph.
@never_cache
def plotData(request,caseId,featureId, startTime, endTime):
	allowedClasses=[]
	for c in Plot.__subclasses__():
		allowedClasses.append(c.__name__)
	feature=get_object_or_404(CaseFeature, case__pk=caseId, pk=featureId, name__in=allowedClasses)
	return HttpResponse(json.dumps(feature.getSeries(startTime, endTime)), content_type="application/json")

## Gets the time the data used in the plot was last updated in string format encoded in a JSON object.
def plotUpdateTime(request,caseId, featureId):
	allowedClasses=[]
	for c in Plot.__subclasses__():
		allowedClasses.append(c.__name__)
	feature=get_object_or_404(CaseFeature, case__pk=caseId, pk=featureId, name__in=allowedClasses)
	data={
		'lastUpdated':str(feature.getLastUpdateTime())
		}
	return HttpResponse(json.dumps(data), content_type="application/json")

## Gets the bounds of the plot, usually the timestep, but could be any numeric identifier. This is used
# to populate the values for the slider bar in the GUI. 
def plotTimeRange(request, caseId, featureId):
	allowedClasses=[]
	for c in Plot.__subclasses__():
		allowedClasses.append(c.__name__)
	feature=get_object_or_404(CaseFeature, case__pk=caseId, pk=featureId, name__in=allowedClasses)
	data={
			'minTime':feature.getMinTime(),
			'maxTime':feature.getMaxTime(),
		}
	return HttpResponse(json.dumps(data), content_type="application/json")

## Renders the plot template with the specified feature.
def plotView(request, caseId, featureId):
	allowedClasses=[]
	for c in Plot.__subclasses__():
		allowedClasses.append(c.__name__)
	feature=get_object_or_404(CaseFeature, case__pk=caseId, pk=featureId, name__in=allowedClasses)
	return render_to_response('percyval/features/plot/plotView.html',{
		'feature':feature,
	},context_instance=RequestContext(request))
