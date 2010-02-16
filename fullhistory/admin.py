from django.contrib import admin
from django.conf.urls.defaults import patterns, url
import fullhistory
import views

class FullHistoryAdminSite(admin.AdminSite):
    def get_urls(self): #django 1.1
        urls = super(FullHistoryAdminSite, self).get_urls()
        
        def wrap(view, model):
            def wrapper(*args, **kwargs):
                kwargs['model'] = model
                return self.admin_view(view)(*args, **kwargs)
            return wrapper
        
        for model in fullhistory.REGISTERED_MODELS.keys():
            if model in self._registry:
                continue
            info = self.name, model._meta.app_label, model._meta.module_name
            urls += patterns('',
                url(r'^%s/%s/(?P<object_id>.+)/history/$' % (model._meta.app_label, model._meta.module_name), 
                    wrap(self.history_view, model),
                    name='%sadmin_%s_%s_history' % info),
                (r'^%s/%s/(?P<object_id>.+)/history/audit/$' % (model._meta.app_label, model._meta.module_name), 
                    wrap(self.history_audit_view, model)),
                url(r'^%s/%s/(?P<object_id>.+)/history/version/(?P<version>\d+)/$' % (model._meta.app_label, model._meta.module_name), 
                    wrap(self.history_version_view, model),
                    name='%sadmin_%s_%s_history_version' % info),
            )
        return urls

    def history_view(self, request, object_id, model):
        opts = model._meta
        return views.history_log(request, 
                                 object_id, 
                                 model, 
                                 ("admin/%s/%s/object_fullhistory.html" % (opts.app_label, opts.object_name.lower()),
                                  "admin/%s/object_fullhistory.html" % opts.app_label,
                                  "admin/object_fullhistory.html"),
                                {'root_path': self.root_path,
                                 'admin_name': getattr(self, 'name', 'admin'),})
    
    def history_audit_view(self, request, object_id, model):
        opts = model._meta
        return views.history_audit(request, 
                                   object_id, 
                                   model, 
                                   ("admin/%s/%s/object_audit_fullhistory.html" % (opts.app_label, opts.object_name.lower()),
                                    "admin/%s/object_audit_fullhistory.html" % opts.app_label,
                                    "admin/object_audit_fullhistory.html"),
                                   {'root_path': self.root_path,
                                    'admin_name': getattr(self, 'name', 'admin'),})

    def history_version_view(self, request, object_id, version, model):
        opts = model._meta
        return views.history_version(request, 
                                     object_id, 
                                     version,
                                     model,
                                     ("admin/%s/%s/object_version_fullhistory.html" % (opts.app_label, opts.object_name.lower()),
                                      "admin/%s/object_version_fullhistory.html" % opts.app_label,
                                      "admin/object_version_fullhistory.html"),
                                     {'root_path': self.root_path,
                                      'admin_name': getattr(self, 'name', 'admin'),})

class FullHistoryAdmin(admin.ModelAdmin):
    def __call__(self, request, url): #django 1.0
        if url:
            new_url = url+'/'
        else:
            new_url = ''
        for pattern in self.get_urls():
            try:
                match = pattern.resolve(new_url)
            except urlresolvers.Resolver404:
                pass
            else:
                if match:
                    return match[0](request, *match[1], **match[2])
        return super(FullHistoryAdmin, self).__call__(request, url)

    def get_urls(self): #django 1.1
        super_model = super(FullHistoryAdmin, self)
        if hasattr(super_model, 'get_urls'):
            urls = super_model.get_urls()
            wrap = self.admin_site.admin_view
        else:
            urls = []
            from django.views.decorators.cache import never_cache
            from django.utils.functional import update_wrapper
            def wrap(view):
                def wrapper(request, *args, **kwargs):
                    if not self.admin_site.has_permission(request):
                        return self.admin_site.login(request)
                    return view(request, *args, **kwargs)
                wrapper = never_cache(wrapper)
                return update_wrapper(wrapper, view)    
        info = getattr(self.admin_site, 'name', 'admin'), self.model._meta.app_label, self.model._meta.module_name
        my_urls = patterns('',
            url(r'^(.+)/history/$', 
                wrap(self.history_view), 
                name='%sadmin_%s_%s_history' % info),
            (r'^(.+)/history/audit/$', wrap(self.history_audit_view)),
            url(r'^(?P<object_id>.+)/history/version/(?P<version>\d+)/$', 
                wrap(self.history_version_view),
                name='%sadmin_%s_%s_history_version' % info),
        )
        return my_urls + urls
    
    def history_view(self, request, object_id):
        opts = self.model._meta
        return views.history_log(request, 
                                 object_id, 
                                 self.model, 
                                 ("admin/%s/%s/object_fullhistory.html" % (opts.app_label, opts.object_name.lower()),
                                  "admin/%s/object_fullhistory.html" % opts.app_label,
                                  "admin/object_fullhistory.html"),
                                {'root_path': self.admin_site.root_path,
                                 'admin_name': getattr(self.admin_site, 'name', 'admin'),})
    
    def history_audit_view(self, request, object_id):
        opts = self.model._meta
        return views.history_audit(request, 
                                   object_id, 
                                   self.model, 
                                   ("admin/%s/%s/object_audit_fullhistory.html" % (opts.app_label, opts.object_name.lower()),
                                    "admin/%s/object_audit_fullhistory.html" % opts.app_label,
                                    "admin/object_audit_fullhistory.html"),
                                   {'root_path': self.admin_site.root_path,
                                    'admin_name': getattr(self.admin_site, 'name', 'admin'),})

    def history_version_view(self, request, object_id, version):
        opts = self.model._meta
        return views.history_version(request, 
                                     object_id, 
                                     version,
                                     self.model, 
                                     ("admin/%s/%s/object_version_fullhistory.html" % (opts.app_label, opts.object_name.lower()),
                                      "admin/%s/object_version_fullhistory.html" % opts.app_label,
                                      "admin/object_version_fullhistory.html"),
                                     {'root_path': self.admin_site.root_path,
                                      'admin_name': getattr(self.admin_site, 'name', 'admin'),})

    def log_addition(self, request, obj):
        fullhistory.adjust_history(obj, 'A')

    def log_change(self, request, obj, message):
        fullhistory.adjust_history(obj, 'U')

    def log_deletion(self, *args, **kwargs):
        return

    def construct_change_message(self, *args, **kwargs):
        return ''

