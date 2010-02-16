from django.conf.urls.defaults import *

from admin import FullHistoryAdminSite

fullhistory_admin = FullHistoryAdminSite()

urlpatterns = patterns('',
    # Uncomment the next line to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

if hasattr(fullhistory_admin, 'urls'):
    urlpatterns += patterns('', (r'^admin/', include(fullhistory_admin.urls)))
else:
    urlpatterns += patterns('', (r'^admin/(.*)', fullhistory_admin.root))

