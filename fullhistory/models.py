from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder, simplejson

import datetime

ENCODER = DjangoJSONEncoder()

class Request(models.Model):
    user_name = models.CharField(max_length=255, blank=True, null=True)
    user_pk = models.PositiveIntegerField(null=True, db_index=True)
    request_path = models.CharField(max_length=255, blank=True, null=True)

    def user(self):
        '''
        Returns the user entry responsible for this change
        May return User.DoesNotExist if the user was deleted
        '''
        if self.user_pk is None:
            return None
        return User.objects.get(pk=self.user_pk)

    def __unicode__(self):
        return self.request_path

class FullHistoryManager(models.Manager):
    def user_actions(self, user):
        return self.get_query_set().filter(user_pk=user.pk)
    
    def actions_for_object(self, entry=None, model=None, pk=None):
        '''
        Retries all revisions for an object
        Requires either entry or model and pk
        '''
        if entry:
            pk = entry.pk
            ct = ContentType.objects.get_for_model(entry)
        else:
            ct = ContentType.objects.get_for_model(model)
        return self.get_query_set().filter(content_type=ct, object_id=pk).order_by('revision')

    def audit(self, entry=None, model=None, pk=None):
        '''
        Performs an audit on an entry, raise an AssertionError if it fails
        Checks that all previous and new values are consistent
        Returns the last known state of the given entry
        '''
        obj = self.get_version(entry, model, pk)
        if entry is not None:
            from fullhistory import REGISTERED_MODELS
            handler = REGISTERED_MODELS[type(entry)]
            for key, value in handler.get_all_data(entry).items():
                #!Truncates microseconds for datetime fields
                if isinstance(value, datetime.datetime):
                    value = str(value.replace(microsecond=0))
                assert obj[key] == value, ('%s does not match %s for attr %s' % 
                                           (obj[key], value, key))
        return obj
    
    def get_version(self, entry=None, model=None, 
                    pk=None, version=None, audit=True):
        '''
        Returns a dictionary representing the object at a given version
        '''
        if version is None:
            histories = self.actions_for_object(entry, model, pk)
        else:
            histories = self.actions_for_object(entry, model, pk).filter(revision__lte=version)
        if audit:
            assert histories[0].action == 'C', 'First action should be create'
        obj = dict()
        for history in histories:
            if history.data is None:
                assert history.action == 'D'
                continue
            for key, value in history.data.items():
                if len(value) == 2:
                    if audit:
                        assert obj[key] == value[0], ('%s does not match %s for attr %s' % 
                                                      (obj[key], value[0], key))
                    obj[key] = value[1]
                else:
                    obj[key] = value[0]
        return obj
    
    def rollback(self, entry=None, model=None, pk=None, 
                 version=None, commit=True, audit=True):
        '''
        Rollback an object to a certain revision number
        '''
        from fullhistory import REGISTERED_MODELS
        data = self.get_version(entry, model, pk, version, audit)
        if model is None:
            model = type(entry)
        obj = REGISTERED_MODELS[model].get_object(data)
        if commit:
            obj.save()
        return obj

ACTIONS = (('C', 'Create'), ('U', 'Update'), ('D', 'Delete'))

class FullHistory(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.CharField(max_length=255)
    revision = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()
    
    action_time = models.DateTimeField(auto_now_add=True)
    _data = models.TextField(db_column='data')
    request = models.ForeignKey(Request, null=True, blank=True)
    site = models.ForeignKey(Site, default=Site.objects.get_current)
    action = models.CharField(max_length=1, choices=ACTIONS)
    info = models.TextField()
    
    objects = FullHistoryManager()

    def set_data(self, val):
        self._data = ENCODER.encode(val)

    def get_data(self):
        return simplejson.loads(self._data)

    data = property(get_data, set_data)

    def action_display(self):
        return dict(ACTIONS)[self.action]
    
    def user(self):
        '''
        Returns the user entry responsible for this change
        May return User.DoesNotExist if the user was deleted
        '''
        if self.request is None:
            return None
        return self.request.user()

    def create_info(self):
        '''
        Generates a summary description of this history entry
        '''
        user_name = u'(System)'
        if self.request:
            user_name = self.request.user_name
        ret = list()
        ret.append({'C':u'%s Created',
                    'U':u'%s Updated',
                    'D':u'%s Deleted',}[self.action] % user_name)
        if self.action == 'U':
            for key, value in self.data.items():
                if not isinstance(value, tuple) or len(value) != 2: 
                    #fix for old admin
                    continue
                ret.append(u'"%s" changed from [%s] to [%s]' % 
                           (key, 
                            unicode(value[0])[:50], 
                            unicode(value[1])[:50]))
        return '\n'.join(ret)
    
    def previous(self):
        '''
        Retrieves the previous history entry for this object
        '''
        return FullHistory.objects.get(content_type=self.content_type,
                                       object_id=self.object_id,
                                       revision=self.revision-1)
    
    def next(self):
        '''
        Retrieves the next history entry for this object
        '''
        return FullHistory.objects.get(content_type=self.content_type,
                                       object_id=self.object_id,
                                       revision=self.revision+1)

    def related_changes(self):
        '''
        Returns a queryset of the changes that have also occurred with this change
        '''
        if self.request:
            return FullHistory.objects.filter(request=self.request).exclude(pk=self.pk)
        return FullHistory.objects.none()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.revision = len(FullHistory.objects.filter(content_type=self.content_type, 
                                                           object_id=self.object_id))
        if not self.info:
            self.info = self.create_info()
        return super(FullHistory, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s %s %s' % (self.content_type, 
                              self.object_id, 
                              self.action_time)

    objects = FullHistoryManager()
    
    class Meta:
        verbose_name_plural = _("full histories")
        get_latest_by = "revision"
        unique_together = (('revision', 'content_type', 'object_id'),)

class HistoryField(generic.GenericRelation):
    def __init__(self, **kwargs):
        return super(HistoryField, self).__init__(FullHistory, **kwargs)

