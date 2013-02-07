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
import subprocess
import datetime
import math
import time
import os
import re
import csv
import logging
from django.core.cache import cache
from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings

log = logging.getLogger(__name__)

## This is the base feature class, all features inherit from this. Features
#  Implement underlying functionality within the tool, cases have features,  such as
#  Images and Movies, the Feature Implementation is responsible for getting the 
#  appropriate information on behalf of the view.
#  
class Feature(object):
	friendlyName="Unnamed Feature"
	def __init__(self,feature):
		self.feature=feature

	## Returns an absolute url to the main page of the feature.  Use Reverse to figure out the
	# correct url.
	def get_absolute_url(self):
		raise NotImplementedError

	## Returns a string of the date and time the data was last updated.
	def getLastUpdateTime(self):
		raise NotImplementedError
	
	## Returns a string of the description of the feature, stored either in the db or the 
	# class.
	def getDescription(self):
		try:
			return self.feature.options.get(name='description').value
		except:
			pass
		try:
			return self.featureDescription
		except:
			pass
		return None

## Base class for plotting, subclass this and supply the appropriate data.
class Plot(Feature):
	friendlyName="Data Plot"
	featureDescription="Generic data plotting"
	## Returns the URL for this case and this specific feature.
	def get_absolute_url(self):
		return reverse('percyval.views.plotView', args=[str(self.feature.case.id),str(self.feature.id)])
	## Returns the value of the first data point or timestep in the series
	def getMinTime(self):
		raise NotImplementedError
	
	## Returns the value of the last datapoint or timestep in the series.
	def getMaxTime(self):
		raise NotImplementedError
	## Returns the time the data was last updated.
	def getLastUpdateTime(self):
		raise NotImplementedError
	## returns the data in flot format for the plot between the provided times.
	def getSeries(self, startTime, endTime):
		raise NotImplementedError

## Parser for FOAM log files
class FOAMLog(object):
	## Gets the name of the logfile from the database, if that fails tries to find a suitable default.
	def logFile(self):
		try:
			return self.feature.options.get(name='logFile').value
		except:
			return "log.pisoFoam"
	## Return the fully qualified path to the log file.
	def logFilePath(self):
		path=os.path.join(settings.MEDIA_ROOT, self.feature.case.options.get(name='caseDir').value.lstrip("/"), self.logFile())
		log.debug("FOAMLog: Log File Path: %s" % path)
		return path

	## Does a stat on the log file to get the time it was last modified.
	def getLastUpdateTime(self):
		time=datetime.datetime.utcfromtimestamp(os.path.getmtime(self.logFilePath()))
		log.debug("FOAMLog: Last Update Time: %s" %time)
		return time
	
	## Gets the first timestep in the log file
	def getMinTime(self):
		residuals=self.processLog()['residuals']
		field=residuals.keys()[0]
		data=residuals[field]['data']
		return data[0][0]

	## Gets the last timestep in the log file
	def getMaxTime(self):
		residuals=self.processLog()['residuals']
		field=residuals.keys()[0]
		data=residuals[field]['data']
		return data[-1][0]

	## Processes the log file and retrieves the residuals and the forces.
	def processLog(self):
		try:
			return self._logData
		except:
			pass
		cacheKey="FOAMLOG_"+self.logFilePath()
		logData=cache.get(cacheKey)
		if logData:
			self._logData=logData
			return self._logData

		residuals={}
		forces={}

		r=open(self.logFilePath(), 'rb')
		time=0
		searchCoeffs=False
		for line in r.readlines():
			if line.startswith("Time = "):
				time=float(line[7:])
				searchCoeffs=False
			if line.startswith("DILUPBiCG"):
			#if line.startswith("smoothSolver") or line.startswith("GAMG") or line.startswith("DILUPBiCG"):
				words=line.split()
				fname=words[3].rstrip(",")
				fvalue=float(words[7].rstrip(","))
				try:
					series=residuals[fname]
				except KeyError:
					residuals[fname]={
						'name':fname,
						'data':[]
					}
					series=residuals[fname]
				series['data'].append([time,fvalue])
			if line.startswith("forceCoeffs output:"):
				searchCoeffs=True
				continue
			if searchCoeffs:
				if not line.startswith(" "):
					searchCoeffs=False
					continue
				(name,equals,value)=line.partition("=")
				value=float(value)
				try:
					series=forces[name]
				except KeyError:
					forces[name]={
							'name':name,
							'data':[],
							}
					series=forces[name]
				series['data'].append([time,value])

		for series in residuals.keys():
			residuals[series]['data'].sort(key=lambda d: d[0])

		logData={'residuals':residuals,
				'forces':forces,}
		self._logData=logData
		cache.set(cacheKey, self._logData,120)
		return self._logData

## Plotting implementation for FOAM residuals.
class FOAMResiduals(Plot, FOAMLog):
	friendlyName="Residuals" 
	## Gets the dictionary of residual values from the FOAM log file, sorted by name.
	# Filters out any time stamps that are not in range.
	def getSeries(self,startTime, endTime):
		log=sorted(self.processLog()['residuals'].values(),key=lambda s: s['name'])
		data=[]
		for series in log:
			s={}
			s['key']=series['name']
			s['values']=[]
			for entry in series['data']:
				if (entry[0] >= float(startTime)) and ( entry[0]<=float(endTime) ):
					s['values'].append({'x':entry[0],'y':entry[1]})
			while(len(s['values'])*len(log) > 15000):
				s['values']=s['values'][::2]
			data.append(s)
		return data

	## Gets the last update time from the foam log file.
	def getLastUpdateTime(self):
		return FOAMLog.getLastUpdateTime(self)

	## Gets the latest time step in the log file.
	def getMaxTime(self):
		return FOAMLog.getMaxTime(self)

	## Gets the first time step in the log file.
	def getMinTime(self):
		return FOAMLog.getMinTime(self)

## Plotting implementation for foam force coefficiants.
class FOAMForces(Plot, FOAMLog):
	friendlyName="Forces" 
	def getSeries(self,startTime, endTime):
		log=sorted(self.processLog()['forces'].values(),key=lambda s: s['name'])
		for series in log:
			try:
				while(series['data'][0][0]<float(startTime)):
					series['data'].pop(0)
				while(series['data'][-1][0]>float(endTime)):
					series['data'].pop(-1)
			except IndexError:
				pass
		return log

	def getLastUpdateTime(self):
		return FOAMLog.getLastUpdateTime(self)
	def getMaxTime(self):
		return FOAMLog.getMaxTime(self)

	def getMinTime(self):
		return FOAMLog.getMinTime(self)





## Searches for movies in the case directory
class MovieGallery(Feature):
	friendlyName="Movies"
	def get_absolute_url(self):
		return reverse('percyval.views.movieList', args=[str(self.feature.case.id)])
	def getLastUpdateTime(self):
		return self.getMovies()[0]['mTimeString']

	def getMovies(self):
		try:
			return self._movies
		except AttributeError:
			pass
		base=os.path.join(settings.MEDIA_ROOT, self.feature.case.options.get(name='caseDir').value)
		movies=[]
		for entry in os.listdir(base):
			dir=os.path.join(base,entry)
			if os.path.isdir(dir):
				try:
					for file in os.listdir(dir):
						path=os.path.join(dir,file)
						if ( file.endswith(".webm")):
							path=path[len(base):]
							path=path.lstrip("/")
							data={
								'name':os.path.basename(file)[:-5],
								'URL':os.path.join(self.feature.case.options.get(name='caseDir').value,path),
								'mTime':os.path.getmtime(os.path.join(base,path)),
								'mTimeString':time.strftime("%Y-%m-%d %I:%M:%S %p",time.localtime(os.path.getmtime(os.path.join(base,path)))),
							}
							movies.append(data)
				except OSError:
					pass
		self._movies=movies
		return movies

	def getMoviePath(self, movie):
		caseDir=os.path.join(settings.MEDIA_URL, self.feature.case.options.get(name='caseDir').value)
		movie=os.path.join(caseDir,movie)
		if not ( movie.endswith(".webm")):
			raise ValueError
		if not os.path.isfile(movie):
			raise ValueError
		return movie

class WebGLScenes(Feature):
	friendlyName="3D Scenes"
	def get_absolute_url(self):
		return reverse('percyval.views.sceneList', args=[str(self.feature.case.id)])
	def getLastUpdateTime(self):
		scenes=self.getScenes()
		log.debug(scenes)
		return scenes.values()[0].values()[0]['mTimeString']
	def getSceneList(self):
		scenes=[]
		for scene in self.getScenes().values():
			subScenes=sorted(scene.values(), key=lambda k: k['mTime'], reverse=True)
			scenes.append({
				'name':subScenes[0]['scene'],
				'mTimeString':subScenes[0]['mTimeString'],
				'mTime':subScenes[0]['mTime'],
				'subScenes':subScenes,
				})
		return sorted(scenes, key=lambda k: k['mTime'], reverse=True)


	def getScenes(self):
		try:
			return self._scenes
		except AttributeError:
			pass
		cacheKey="WEBGLSCENSE_%s" % self.feature.id
		#scenes=cache.get(cacheKey)
		#if scenes:
		#	self._scenes=scenes
		#	return self._scenes

		base=os.path.join(
				settings.MEDIA_ROOT, 
				self.feature.case.options.get(name='caseDir').value.lstrip("/"),
				"WebGL")
		log.debug("getScenes: Media Root: %s" % settings.MEDIA_ROOT)
		log.debug("getScenes: Base: %s" %base)
		scenes={}
		if not os.path.exists(base):
			return scenes
		if not os.path.isdir(base):
			return scenes
		for entry in os.listdir(base):
			dir=os.path.join(base,entry)
			if os.path.isdir(dir):
				try:
					for file in os.listdir(dir):
						path=os.path.join(dir,file)
						if file.endswith(".html"):
							path=path[len(base):]
							path=path.lstrip("/")
							data={
									'scene':entry,
									'localPath':os.path.join(base,path),
									'name':os.path.basename(path),
									'URL':os.path.join(self.feature.case.options.get(name='caseDir').value,"WebGL",path),
									'mTime':os.path.getmtime(os.path.join(base,path)),
									'mTimeString':time.strftime("%Y-%m-%d %I:%M:%S %p",time.localtime(os.path.getmtime(os.path.join(base,path)))),
									}
							try:
								scenes[entry][path]=data
							except:
								scenes[entry]={path:data}
				except OSError:
					pass
		self._scenes=scenes
		cache.set(cacheKey, self._scenes,120) 
		return self._scenes





## Searches for images in the case directory
class ImageGallery(Feature):
	friendlyName="Images"
	def get_absolute_url(self):
		return reverse('percyval.views.imageGalleryList', args=[str(self.feature.case.id)])

	# Gets a list of galleries - should be cached eventually.
	def getGalleries(self):
		galleries=[]
		for gallery in self.getImages().values():
			img=sorted(gallery.values(), key=lambda k: k['mTime'], reverse=True)[0]
			galleries.append({
				'name': img['gallery'],
				'URL': reverse("percyval.views.imageGalleryView", args=[self.feature.case.id, img['gallery'] ]),
				'mTimeString': img['mTimeString'],
				'mTime': img['mTime'],
				'image': img['URL'],
			})
		return sorted(galleries, key=lambda k: k['mTime'], reverse=True)

	def getLastUpdateTime(self):
		try:
			return self.getGalleries()[0]['mTimeString']
		except IndexError:
			return None

	def getImages(self):
		try:
			return self._images
		except AttributeError:
			pass
		base=os.path.join(settings.MEDIA_ROOT, self.feature.case.options.get(name='caseDir').value)
		images={}
		for entry in os.listdir(base):
			dir=os.path.join(base,entry)
			if os.path.isdir(dir):
				try:
					for file in os.listdir(dir):
						path=os.path.join(dir,file)
						if ( file.endswith(".jpg") or file.endswith(".png") )and os.path.isfile(path):
							path=path[len(base):]
							path=path.lstrip("/")
							data={
								'gallery':entry,
								'localPath':os.path.join(base,path),
								'name':os.path.basename(path),
								'URL':os.path.join(self.feature.case.options.get(name='caseDir').value,path),
								'mTime':os.path.getmtime(os.path.join(base,path)),
								'mTimeString':time.strftime("%Y-%m-%d %I:%M:%S %p",time.localtime(os.path.getmtime(os.path.join(base,path)))),
							}
							try:
								images[entry][path]=data
							except:
								images[entry]={path:data}
				except OSError:
					pass
		self.images=images
		return images

	def getImagePath(self, image):
		caseDir=self.feature.case.options.get(name='caseDir').value
		image=os.path.join(caseDir,image)
		if not ( image.endswith(".jpg") or image.endswith(".png") ):
			raise ValueError
		if not os.path.isfile(image):
			raise ValueError
		return image
		


## Cases store information about active cases
class Case(models.Model):
	name=models.CharField(
			help_text="Give the case a meaningful name, this will be shown in the GUI whenever the case is referenced",
			verbose_name="Case Name",
			max_length=128,
			)
	owner=models.ForeignKey(User, related_name="cases")
	description=models.TextField(blank=True)

	def __unicode__(self):
		return u'%s' % self.name
	def __str__(self):
		return self.name
	def get_absolute_url(self):
		return reverse('percyval.views.caseDefaultView', args=[str(self.id)])

	def getLastUpdateTime(self):
		for f in self.features.all():
			try:
				return f.getLastUpdateTime()
			except:
				pass
		return "Unknown"

## CaseOptions are options associated with cases, multiple options with the same name can exist, this allows users to specify
#  options for the entire case, such as its location
class CaseOption(models.Model):
	case=models.ForeignKey(Case, related_name="options", help_text="The case this option relates to", verbose_name="Case")
	name=models.CharField(
			help_text="The name of the option",
			verbose_name="Option Name",
			max_length=128,
			)
	value=models.CharField(
			help_text="The value of the option",
			verbose_name="Option Value",
			max_length=128,
			)
	def __unicode__(self):
		return u'%s' % self.name
	def __str__(self):
		return self.name
		
## Case features define which features are supported by a specific case, cases support multiple features
class CaseFeature(models.Model):
	case=models.ForeignKey(Case, related_name="features", help_text="The case this feature relates to", verbose_name="Case")
	name=models.CharField(
			help_text="The name of the supported feature, cases use one or more features to define content.",
			verbose_name="Feature Name",
			max_length=128,
			)
	def __unicode__(self):
		return u'%s' % self.name
	def __str__(self):
		return self.name
	def __getFeature(self):
		try:
			return self.__feature
		except AttributeError:
			c=self.name
			self.__feature=eval("%s"%self.name)(self)
		return self.__feature
	def __getattr__(self, name):
		if name=="_CaseFeature__feature":
			raise AttributeError
		try:
			return getattr(self.__getFeature(), name)
		except NameError:
			raise AttributeError

##FeatureOptions are options associated with features, multiple options with the same name can exist, this allows users to specify
# array of values for a specific option, this is retrieved with the filter or get methods.  Feature options differ from case options
# in that they are associated with the feature registered with the case, and not the case globally
class FeatureOption(models.Model):
	feature=models.ForeignKey(CaseFeature, related_name="options", help_text="The feature this option relates to", verbose_name="Feature")
	name=models.CharField(
			help_text="The name of the option",
			verbose_name="Option Name",
			max_length=128,
			)
	value=models.CharField(
			help_text="The value of the option",
			verbose_name="Option Value",
			max_length=128,
			)
	def __unicode__(self):
		return u'%s' % self.name
	def __str__(self):
		return self.name
