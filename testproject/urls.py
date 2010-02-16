from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
#from fullhistory.admin import FullHistoryAdminSite
from django.contrib import admin
#admin.site = FullHistoryAdminSite()
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'^ticketmanager/', include('ticketmanager.urls')),

    # Uncomment the next line to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

if hasattr(admin.site, 'urls'):
    urlpatterns += patterns('', (r'^admin/', include(admin.site.urls)))
else:
    urlpatterns += patterns('', (r'^admin/(.*)', admin.site.root))

