from django.shortcuts import get_object_or_404, render_to_response
from django.http import Http404
from django.utils.encoding import force_unicode
from django.utils.text import capfirst
from django.template import RequestContext
from django.utils.translation import ugettext as _

from models import FullHistory

def history_log(request, object_id, model, template, extra_context=None):
    opts = model._meta
    app_label = opts.app_label
    obj = get_object_or_404(model, pk=object_id)
    action_list = FullHistory.objects.actions_for_object(obj).select_related()
    context = {
        'title': _(u'Change history: %s') % force_unicode(obj),
        'action_list': action_list,
        'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
        'object': obj,
        'app_label': app_label,
    }
    context.update(extra_context or {})
    return render_to_response(template, context, context_instance=RequestContext(request))

def history_audit(request, object_id, model, template, extra_context=None):
    obj = get_object_or_404(model, pk=object_id)
    failure = None
    try:
        FullHistory.objects.audit(obj)
    except AssertionError, e:
        failure = e
    opts = model._meta
    app_label = opts.app_label
    context = {
        'title': _(u'Audit history: %s') % force_unicode(obj),
        'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
        'object': obj,
        'app_label': app_label,
        'failure': failure,
    }
    context.update(extra_context or {})
    return render_to_response(template, context, context_instance=RequestContext(request))

def history_version(request, object_id, version, model, template, extra_context=None):
    version = int(version)
    try:
        action = FullHistory.objects.actions_for_object(model=model, pk=object_id).get(revision=version)
    except FullHistory.DoesNotExist:
        raise Http404()
    obj = FullHistory.objects.rollback(model=model, pk=object_id, 
                                       commit=False, audit=False, version=version)
    opts = model._meta
    app_label = opts.app_label
    context = {
        'title': _(u'History Version %s for: %s') % (version, force_unicode(obj)),
        'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
        'object': obj,
        'app_label': app_label,
        'version': version,
        'action': action,
    }
    context.update(extra_context or {})
    return render_to_response(template, context, context_instance=RequestContext(request))

