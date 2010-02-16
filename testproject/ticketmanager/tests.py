from django.test import TestCase
from django.core.urlresolvers import reverse

from models import *

class SimpleTest(TestCase):
    fixtures = ('test_data',)

    def test_ticket_listing(self):
        self.assertEquals(200, self.client.get(reverse('ticketmanager.views.ticket_list')).status_code)

    def test_ticket_creation(self):
        self.assertEquals(200, self.client.get(reverse('ticketmanager.views.ticket_create')).status_code)
        self.assertEquals(200, self.client.post(reverse('ticketmanager.views.ticket_create')).status_code)
        self.fail('Not fully tested')

    def test_ticket_detail(self):
        for ticket in Ticket.objects.all():
            self.assertEquals(200, self.client.get(ticket.get_absolute_url()).status_code)

    def test_ticket_comment(self):
        for ticket in Ticket.objects.all():
            self.client.post(reverse('ticketmanager.views.post_comment', kwargs={'ticket_id':ticket.pk}))
        self.fail('Not fully tested')

    def test_ticket_attachment(self):
        for ticket in Ticket.objects.all():
            self.client.post(reverse('ticketmanager.views.post_attachment', kwargs={'ticket_id':ticket.pk}))
        self.fail('Not fully tested')

