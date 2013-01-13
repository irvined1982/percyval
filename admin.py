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

from django.contrib import admin
from percyval.models import *
class FeatureInline(admin.TabularInline):
	model = CaseFeature

class CaseOptionInline(admin.TabularInline):
	model=CaseOption

class CaseAdmin(admin.ModelAdmin):
	inlines = [
		FeatureInline,
		CaseOptionInline,
	]

class FeatureOptionInline(admin.TabularInline):
	model=FeatureOption

class FeatureAdmin(admin.ModelAdmin):
	inlines=[
			FeatureOptionInline,
			]

admin.site.register(Case, CaseAdmin)
admin.site.register(CaseFeature, FeatureAdmin)
