from django.db import models
from django.contrib.auth.models import User

import fullhistory
from fullhistory.models import HistoryField, FullHistory

# Create your models here.
class AbstractCategory(models.Model):
    title = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(default=0)

    def __unicode__(self):
        return self.title

    class Meta:
        abstract = True
        ordering = ('order',)

class Milestone(AbstractCategory):
    pass

class Component(AbstractCategory):
    pass

class Version(AbstractCategory):
    pass

class TriageState(AbstractCategory):
    pass

class Parameter(AbstractCategory):
    pass

class Ticket(models.Model):
    summary = models.CharField(max_length=100)
    description = models.TextField()
    reported_by = models.ForeignKey(User, blank=True, null=True, related_name='reported_tickets')
    assigned_to = models.ForeignKey(User, blank=True, null=True, related_name='assigned_tickets')
    milestone = models.ForeignKey(Milestone, blank=True, null=True)
    component = models.ForeignKey(Component, blank=True, null=True)
    version = models.ForeignKey(Version, blank=True, null=True)
    keywords = models.CharField(max_length=255, blank=True)
    cc = models.TextField(blank=True)
    triage_state = models.ForeignKey(TriageState)
    parameters = models.ManyToManyField(Parameter, blank=True)

    time_opened = models.DateTimeField(auto_now_add=True)
    time_updated = models.DateTimeField(auto_now=True)

    history = HistoryField()

    def __unicode__(self):
        return self.summary

    @models.permalink
    def get_absolute_url(self):
        return ('ticketmanager.views.ticket_detail', [str(self.pk)])

    class Meta:
        ordering = ('time_updated',)

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket)
    user = models.ForeignKey(User, blank=True, null=True)
    attachment = models.FileField(upload_to='ticket-attachments')
    description = models.TextField(blank=True)
    time_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'%s: %s' % (self.ticket, self.attachment.name)

class Comment(models.Model):
    ticket = models.ForeignKey(Ticket)
    user = models.ForeignKey(User, blank=True, null=True)
    description = models.TextField()
    history = models.ForeignKey(FullHistory, blank=True, null=True)
    
    def update_history(self):
        try:
            self.history = (self.ticket.history.all() & fullhistory.get_active_histories()).latest()
        except FullHistory.DoesNotExist:
            pass

fullhistory.register_model(Ticket)

