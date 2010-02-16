from django.template import Library
from django.core import urlresolvers

register = Library()

@register.filter
def admin_history_version_link(history, admin_name):
    try:
        return urlresolvers.reverse('%sadmin_%s_%s_history_version' % (admin_name,
                                                                       history.content_type.app_label, 
                                                                       history.content_type.model), 
                                    kwargs={'object_id':history.object_id, 'version':history.revision})
    except:
        return None
