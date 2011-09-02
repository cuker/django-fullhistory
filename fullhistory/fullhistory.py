try:
    import thread
except ImportError:
    import dummy_thread as thread

from django.db.models import signals
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType

from models import FullHistory, Request
from signals import post_create, post_adjust
from serializers import Serializer, Deserializer

# The state is a dictionary of lists. The key to the dict is the current
# thread and the list is handled as a stack of values.
STATE = {}

def get_active_histories():
    '''
    Returns histories that have been created during the current request
    '''
    request, rq = STATE.get(thread.get_ident(), (None, None))
    if rq is None:
        return FullHistory.objects.none()
    return FullHistory.objects.filter(request=rq)

def get_or_create_request():
    '''
    Returns a request instance that is global for this request
    If this function is called outside of a web request then the user_name is marked as system
    '''
    thread_ident = thread.get_ident()
    request, rq = STATE.get(thread_ident, (None, None))
    if not rq:
        rq = Request()
        if request:
            rq.request_path = request.path
            if request.user.is_anonymous():
                rq.user_name = u'(Anonymous)'
            else:
                rq.user_pk = request.user.pk
                rq.user_name = unicode(request.user)[:255]
        else:
            rq.user_name = u'(System)'
        rq.save()
        STATE[thread_ident] = (request, rq)
    return rq

class FullHistoryHandler(object):
    '''
    This class is responsible for handling and generating change logs for the model it is bound to
    '''
    def __init__(self, model):
        self.model = model

    def prepare_initial(self, entry):
        '''
        Records the state of an object
        '''
        entry._fullhistory = self.get_all_data(entry)

    def get_difference(self, entry):
        '''
        Given an object it returns a dictionary of tuples
        Each key of the dictionary is an attribute of the object
        Each tuple is the previous and current value
        '''
        ret = dict()
        newdata = self.get_all_data(entry)
        keys = set(newdata.keys()) | set(entry._fullhistory.keys())
        for key in keys:
            oldvalue = entry._fullhistory.get(key, None)
            newvalue = newdata.get(key, None)
            if oldvalue != newvalue:
                ret[key] = (oldvalue, newvalue)
        return ret

    def get_all_data(self, entry):
        '''
        Returns a dictionary of all persistant values of an object
        '''
        serializer = Serializer()
        serial = serializer.serialize([entry])
        serial = serial[0]
        serial['fields'][entry._meta.pk.name] = serial['pk']
        return serial['fields']

    def get_all_data_tuple(self, entry):
        data = self.get_all_data(entry)
        for key, value in data.items():
            data[key] = (value,)
        return data

    def get_object(self, data):
        info = {'pk': data.pop(self.model._meta.pk.name, None),
                'model': "%s.%s" % (self.model._meta.app_label, self.model._meta.object_name.lower()),
                'fields': data}
        return list(Deserializer([info]))[0]

    def create_history(self, entry, action):
        '''
        Returns a FullHistory object recording the change of the object provided
        '''
        request = get_or_create_request()
        if action == 'U':
            data = self.get_difference(entry)
            if len(data) == 0:
                data = self.get_all_data_tuple(entry)
        elif action == 'C':
            data = self.get_all_data_tuple(entry)
        else:
            data = None
        fh = FullHistory(data=data, 
                         content_object=entry, 
                         action=action, 
                         request=request)
        fh.save()
        self.apply_parents(entry, lambda x: self.create_history(x, action))
        self.prepare_initial(entry)
        post_create.send(sender=type(entry), fullhistory=fh, instance=entry)
        return fh

    def adjust_history(self, obj, action='U'):
        '''
        Adjusts the latest entry to accomidate any changes not picked up
        Likely changes are ManyToManyFields
        '''
        delta = self.get_difference(obj)
        if delta:
            ct = ContentType.objects.get_for_model(obj)
            try:
                history = get_active_histories().filter(content_type=ct, 
                                                        object_id=obj.pk).latest()
            except FullHistory.DoesNotExist:
                history = FullHistory(content_object=obj,
                                      request=get_or_create_request(), 
                                      action=action, 
                                      data=dict())
            if history.action == 'C':
                for key, value in delta.items():
                    delta[key] = (value[1],)
            data = history.data
            data.update(delta)
            history.data = data
            history.info = history.create_info()
            history.save()
            self.prepare_initial(obj)
            post_adjust.send(sender=type(obj), 
                             fullhistory=history, 
                             instance=obj)
            return history
        return None

    def apply_parents(self, instance, func):
        '''
        Iterates through all non-abstract inherited parents and applies the supplied function
        '''
        for field in instance._meta.parents.values():
            if field and getattr(instance, field.name, None):
                func(getattr(instance, field.name))

REGISTERED_MODELS = dict()

def init_history_signal(instance, **kwargs):
    if instance.pk is not None:
        handler = REGISTERED_MODELS[type(instance)]
        try:
            handler.prepare_initial(instance)
            handler.apply_parents(instance, handler.prepare_initial)
        except ObjectDoesNotExist:
            pass

def save_history_signal(instance, created, **kwargs):
    try:
        REGISTERED_MODELS[type(instance)].create_history(instance, created and 'C' or 'U')
    except ObjectDoesNotExist:
        pass

def delete_history_signal(instance, **kwargs):
    REGISTERED_MODELS[type(instance)].create_history(instance, 'D')

def end_session():
    STATE.pop(thread.get_ident(), None)

def adjust_history(instance, action='U'):
    return REGISTERED_MODELS[type(instance)].adjust_history(instance, action)

def register_model(model, cls=None):
    if model in REGISTERED_MODELS:
        return
    for parent in model._meta.parents.keys():
        register_model(parent, cls)
    if cls is None:
        cls = FullHistoryHandler
    signals.post_init.connect(init_history_signal, sender=model)
    signals.post_save.connect(save_history_signal, sender=model)
    signals.post_delete.connect(delete_history_signal, sender=model)
    REGISTERED_MODELS[model] = cls(model)
    
class FullHistoryMiddleware(object):
    def process_request(self, request):
        STATE[thread.get_ident()] = (request, None)

    def process_response(self, request, response):
        end_session()
        return response

