from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson as json
from django import forms   

try:
    import cPickle as pickle
except ImportError:
    import pickle

class PickledObject(str):
    """A subclass of string so it can be told whether a string is
       a pickled object or not (if the object is an instance of this class
       then it must [well, should] be a pickled one)."""
    pass

def deserialize(value):
    if isinstance(value, basestring):
        try:
            return json.loads(str(value))
        except:
            try:
                return pickle.loads(str(value))
            except:
                return value
    return value

class PickledObjectField(models.Field):
    __metaclass__ = models.SubfieldBase
    
    def to_python(self, value):
        return deserialize(value)
    
    def get_db_prep_save(self, value):
        if value is not None and not isinstance(value, PickledObject):
            value = PickledObject(json.dumps(value, cls=DjangoJSONEncoder))
        return value
    
    def get_internal_type(self): 
        return 'TextField'
    
    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            value = self.get_db_prep_save(value)
            return super(PickledObjectField, self).get_db_prep_lookup(lookup_type, value)
        elif lookup_type == 'in':
            value = [self.get_db_prep_save(v) for v in value]
            return super(PickledObjectField, self).get_db_prep_lookup(lookup_type, value)
        else:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(PickledObjectField, self).formfield(**defaults)

class FullHistoryManager(models.Manager):
    def user_actions(self, user):
        return self.get_query_set().filter(user_pk=user.pk)
    
    def actions_for_object(self, entry):
        ct = ContentType.objects.get_for_model(entry)
        return self.get_query_set().filter(content_type=ct, object_id=entry.pk)

    def audit(self, entry):
        obj = self.get_version(entry)
        for key, value in obj.items():
            assert getattr(entry, key) == value, '%s does not match %s for attr %s' % (getattr(entry, key), value, key)
    
    def get_version(self, entry, version=None, audit=True):
        if version:
            histories = self.actions_for_object(entry)[:version]
        else:
            histories = self.actions_for_object(entry)
        assert histories[0].action == 'C', 'First action should be create'
        obj = histories[0].data
        for history in histories[1:]:
            if history.data is None:
                assert history.action == 'D'
                continue
            for key, value in history.data.items():
                if isinstance(value, tuple):
                    if audit:
                        assert obj[key] == value[0], '%s does not match %s for attr %s' % (obj[key], value[0], key)
                    obj[key] = value[1]
                else:
                    obj[key] = value
        return obj
    
    def rollback(self, entry, version=None, commit=True, audit=True):
        model = type(entry)
        data = self.get_version(entry, version, audit)
        obj = model(**data)
        if commit:
            obj.save()
        return obj
    
    def restore(self, model, pk, version=None, commit=True, audit=True):
        entry = model(pk=pk)
        return self.rollback(entry, version, commit, audit)

class FullHistory(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()
    
    action_time = models.DateTimeField(auto_now=True)
    data = PickledObjectField(null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    user_pk = models.PositiveIntegerField(null=True, db_index=True)
    request_path = models.CharField(max_length=255, blank=True, null=True)
    action = models.CharField(max_length=1, choices=(('C', 'Create'), ('U', 'Update'), ('D', 'Delete')))
    info = models.TextField()
    
    objects = FullHistoryManager()
    
    def user(self):
        return User.objects.get(pk=self.user_pk)

    def change_message(self):
        return self.info

    def create_info(self):
        ret = {'C':u'%s Created',
               'U':u'%s Updated',
               'D':u'%s Deleted',}[self.action] % self.user_name
        if self.action == 'U':
            for key, value in self.data.items():
                if not isinstance(value, tuple) or len(value) != 2: #fix for old admin
                    break
                ret += u'\n"%s" changed from [%s] to [%s]' % (key, unicode(value[0])[:50], unicode(value[1])[:50])
        return ret
    
    def previous(self):
        return FullHistory.objects.filter(content_type=self.content_type,
                                          object_id=self.object_id,
                                          action_time__lt=self.action_time).latest()
    
    def next(self):
        try:
            return FullHistory.objects.filter(content_type=self.content_type,
                                              object_id=self.object_id,
                                              action_time__gt=self.action_time)[0]
        except IndexError:
            raise FullHistory.DoesNotExist()

    def save(self):
        if not self.info:
            self.info = self.create_info()
        return super(FullHistory, self).save()

    def __unicode__(self):
        return u'%s %s %s' % (self.content_type, self.object_id, self.action_time)

    objects = FullHistoryManager()
    
    class Meta:
        verbose_name_plural = u"full histories"
        get_latest_by = "action_time"
        #chronological order
        ordering = ['action_time']


class FullHistoryAdmin(object):
    def history_view(self, request, object_id, extra_context=None):
        from django.shortcuts import get_object_or_404, render_to_response
        from django.utils.translation import ugettext as _
        from django.utils.encoding import force_unicode
        from django.utils.text import capfirst
        from django import template
        
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        obj = get_object_or_404(model, pk=object_id)
        action_list = FullHistory.objects.actions_for_object(obj).select_related().order_by('-action_time')
        # If no history was found, see whether this object even exists.
        context = {
            'title': _('Change history: %s') % force_unicode(obj),
            'action_list': action_list,
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'object': obj,
            'root_path': self.admin_site.root_path,
            'app_label': app_label,
        }
        context.update(extra_context or {})
        return render_to_response(self.object_history_template or [
            "admin/%s/%s/object_history.html" % (opts.app_label, opts.object_name.lower()),
            "admin/%s/object_history.html" % opts.app_label,
            "admin/object_history.html"
        ], context, context_instance=template.RequestContext(request))




