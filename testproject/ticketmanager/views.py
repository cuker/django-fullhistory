from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect
from models import *
from forms import *

def get_forms(obj): 
    return {'object':obj,
            'comment_form':CommentForm(prefix='comment'),
            'ticket_form':UpdateTicketForm(instance=obj, prefix='ticket'),
            'attachment_form':TicketAttachmentForm(prefix='attachment'),}

def ticket_create(request):
    if request.POST:
        ticket_form = TicketForm(request.POST)
        if ticket_form.is_valid():
            ticket = ticket_form.save(commit=False)
            ticket.reported_by = request.user.is_authenticated() and request.user or None
            ticket.save()
            return HttpResponseRedirect(ticket.get_absolute_url())
    else:
        ticket_form = TicketForm()
    return render_to_response('ticketmanager/ticket_create.html',
                              {'ticket_form':ticket_form,})

def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    return render_to_response('ticketmanager/ticket_detail.html', 
                              get_forms(ticket))

def post_comment(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    if request.POST:
        comment_form = CommentForm(request.POST, prefix='comment')
        ticket_form = UpdateTicketForm(request.POST, prefix='ticket', instance=ticket)
        forms = get_forms(ticket)
        forms['comment_form'] = comment_form
        forms['ticket_form'] = ticket_form
        if comment_form.is_valid() and ticket_form.is_valid():
            if ticket_form.changed_data:
                ticket_form.save()
            comment = comment_form.save(commit=False)
            comment.ticket = ticket
            comment.update_history()
            comment.user = request.user.is_authenticated() and request.user or None
            comment.save()
        else:
            attachment_form = TicketAttachmentForm(prefix='attachment')
            return render_to_response('ticketmanager/ticket_detail.html', 
                                      forms)
    return HttpResponseRedirect(ticket.get_absolute_url())

def post_attachment(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    if request.POST:
        attachment_form = TicketAttachmentForm(request.POST, request.FILES, prefix='attachment')
        forms = get_forms(ticket)
        forms['attachment_form'] = attachment_form
        if attachment_form.is_valid():
            attachment = attachment_form.save(commit=False)
            attachment.user = request.user.is_authenticated() and request.user or None
            attachment.ticket = ticket
            attachment.save()
        else:
            comment_form = CommentForm(prefix='comment')
            ticket_form = UpdateTicketForm(prefix='ticket')
            return render_to_response('ticketmanager/ticket_detail.html', 
                                      forms)
    return HttpResponseRedirect(ticket.get_absolute_url())

