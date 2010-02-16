from models import FullHistory
from django.db.models import signals

try:
    import thread
except ImportError:
    import dummy_thread as thread

# The state is a dictionary of lists. The key to the dict is the current
# thread and the list is handled as a stack of values.
state = {}

def enter_fullhistory_management(request):
    thread_ident = thread.get_ident()
    state[thread_ident] = request

def leave_fullhistory_management():
    thread_ident = thread.get_ident()
    if thread_ident in state:
        del state[thread_ident]

def get_request():
    thread_ident = thread.get_ident()
    return state.get(thread_ident, None)

def get_authorizing_user():
    request = get_request()
    if request:
        return request.user
    return None
        
def prepare_initial(entry):
    entry._fullhistory = get_all_data(entry)

def get_difference(entry):
    ret = dict()
    newdata = get_all_data(entry)
    for field in entry._meta.fields:
        oldvalue = entry._fullhistory[field.name]
        newvalue = newdata[field.name]
        if oldvalue != newvalue:
            ret[field.name] = (oldvalue, newvalue)
    return ret

def get_all_data(entry):
    ret = dict()
    for field in entry._meta.fields:
        if getattr(field.rel, 'to', False):
            try:
                ret[field.name] = getattr(entry, field.name).pk
            except:
                ret[field.name] = None
        else:
            try:
                ret[field.name] = getattr(entry, field.name, None)
            except:
                ret[field.name] = None
    return ret

def create_history(entry, action):
    request = get_request()
    if request:
        user = request.user
        request_path = request.path[:255]
    else:
        user = None
        request_path = None
    user_pk = None
    if user:
        if user.is_anonymous():
            user = '(Anonymous)'
        else:
            user_pk = user.pk
            user = str(user)
    else:
        user = '(System)'
    if action == 'U':
        data = get_difference(entry)
    elif action == 'C':
        data = get_all_data(entry)
    else:
        data = None
    if action == 'U' and len(data) == 0:
        data = get_all_data(entry)
    fh = FullHistory(data=data, user_name=user, user_pk=user_pk, content_object=entry, action=action, request_path=request_path)
    fh.save()
    prepare_initial(entry)
    return fh

def init_history_signal(sender, instance, **kwargs):
    prepare_initial(instance)

def save_history_signal(sender, instance, created, **kwargs):
    create_history(instance, created and 'C' or 'U')

def delete_history_signal(sender, instance, **kwargs):
    create_history(instance, 'D')

def register_model(cls):
    signals.post_init.connect(init_history_signal, sender=cls)
    signals.post_save.connect(save_history_signal, sender=cls)
    signals.post_delete.connect(delete_history_signal, sender=cls)
    
class FullHistoryMiddleware(object):
    def process_request(self, request):
        enter_fullhistory_management(request)

    def process_response(self, request, response):
        leave_fullhistory_management()
        return response

