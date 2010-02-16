from django import forms
from models import *

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        exclude = ('user', 'history', 'ticket')

class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        exclude = ('user', 'ticket')

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        exclude = ('reported_by',)

class UpdateTicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        exclude = ('summary', 'description', 'reported_by')

