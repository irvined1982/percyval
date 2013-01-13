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
#  $Rev: 159 $:
#  $Author: irvined $:
#  $Date: 2013-01-05 01:27:49 +0100 (Sat, 05 Jan 2013) $:
from django.conf.urls.defaults import patterns, include, url
from django.views.generic import ListView
from percyval.models import *

urlpatterns = patterns('',
	url(r'^create','percyval.views.caseCreate'),
	url(r'^(\d+)/feature/(\w+)/option/add', 'percyval.views.caseFeatureAdd'),
	url(r'^(\d+)/delete$', 'percyval.views.caseDelete'),
	url(r'^(\d+)/delete/ask$', 'percyval.views.confirmCaseDelete'),
	url(r'^$', ListView.as_view(model=Case)),
	url(r'^(\d+)/$','percyval.views.caseDefaultView'),
	url(r'^(\d+)/movies/$','percyval.views.movieList'),
	url(r'^(\d+)/movies/download/(.+\.webm)$','percyval.views.movieView'),
	url(r'^(\d+)/images/$','percyval.views.imageGalleryList'),
	url(r'^(\d+)/images/gallery/(.+)/$','percyval.views.imageGalleryView'),
	url(r'^(\d+)/images/download/(.+\.jpg)$','percyval.views.imageView'),
	url(r'^(\d+)/images/download/(.+\.png)$','percyval.views.imageView'),

	url(r'^(\d+)/plot/(\d+)/$','percyval.views.plotView'),
	url(r'^(\d+)/plot/(\d+)/plotData/([-+]?[0-9]*\.?[0-9]+)/([-+]?[0-9]*\.?[0-9]+)','percyval.views.plotData'),
	url(r'^(\d+)/plot/(\d+)/updateTime$','percyval.views.plotUpdateTime'),
	url(r'^(\d+)/plot/(\d+)/timeRange$','percyval.views.plotTimeRange'),

)
