from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson as json
from django import http

from hyperadmin.resources import BaseResource

from common import MediaType, BUILTIN_MEDIA_TYPES

class JSON(MediaType):
    def convert_resource(self, resource):
        return {}
    
    def convert_instance(self, instance):
        #instance may be: ApplicationResource or CRUDResource
        result = dict()
        if isinstance(instance, BaseResource):
            result.update(self.convert_resource(instance))
        return result
    
    def convert_form(self, form):
        return self.get_form_instance_values(form)
    
    def convert_item_form(self, form):
        return self.convert_form(form)
    
    def get_payload(self, instance=None, errors=None):
        #CONSIDER a better inferface
        if hasattr(self.view, 'get_items_forms'):
            items = [self.convert_item_form(form) for form in self.view.get_items_forms()]
        else:
            items = [self.convert_instance(item) for item in self.view.get_items()]
        #TODO errors
        if instance:
            return items[0]
        return items
    
    def serialize(self, content_type, instance=None, errors=None):
        data = self.get_payload(instance=instance, errors=errors)
        content = json.dumps(data, cls=DjangoJSONEncoder)
        return http.HttpResponse(content, content_type)
    
    def deserialize(self, form_class, instance=None):
        #TODO this needs more thinking
        if hasattr(self.request, 'body'):
            payload = self.request.body
        else:
            payload = self.request.raw_post_data
        data = json.loads(payload)
        kwargs = self.view.get_form_kwargs()
        kwargs.update({'instance':instance,
                       'data':data,
                       'files':self.request.FILES,})
        form = form_class(**kwargs)
        return form

BUILTIN_MEDIA_TYPES['application/json'] = JSON

class JSONP(JSON):
    def get_jsonp_callback(self):
        #TODO make configurable
        return self.view.request.GET['callback']
    
    def serialize(self, content_type, instance=None, errors=None):
        data = self.get_payload(instance=instance, errors=errors)
        content = json.dumps(data, cls=DjangoJSONEncoder)
        callback = self.get_jsonp_callback()
        return http.HttpResponse(u'%s(%s)' % (callback, content), content_type)

BUILTIN_MEDIA_TYPES['text/javascript'] = JSONP

