try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.default import patterns, url
from models import Ticket

urlpatterns = patterns(
    'ticketmanager.views',
    (r'^create/$', 'ticket_create'),
    (r'^view/(?P<ticket_id>\d+)/$', 'ticket_detail'),
    (r'^view/(?P<ticket_id>\d+)/comment/$', 'post_comment'),
    (r'^view/(?P<ticket_id>\d+)/attachment/$', 'post_attachment'),
)

urlpatterns += patterns(
    '',
    url(
        r'^$',
        'django.views.generic.list_detail.object_list',
        {'queryset': Ticket.objects.all()},
        name='ticketmanager.views.ticket_list'
    ),
)

