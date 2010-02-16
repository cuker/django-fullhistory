from django.contrib import admin
from fullhistory.admin import FullHistoryAdmin

from models import *

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')

admin.site.register(Milestone, CategoryAdmin)
admin.site.register(Component, CategoryAdmin)
admin.site.register(Version, CategoryAdmin)
admin.site.register(TriageState, CategoryAdmin)
admin.site.register(Parameter, CategoryAdmin)

class CommentInline(admin.StackedInline):
    model = Comment

class TicketAttachmentInline(admin.StackedInline):
    model = TicketAttachment

class TicketAdmin(FullHistoryAdmin):
    list_display = ('summary', 'milestone', 'component', 'version', 'triage_state', 'reported_by', 'assigned_to')
    list_filter = ('triage_state', 'milestone', 'component', 'version')
    date_hierarchy = 'time_opened'
    inlines = [CommentInline, TicketAttachmentInline]

admin.site.register(Ticket, TicketAdmin)

