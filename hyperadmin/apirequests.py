import mimeparse


class APIRequest(object):
    """
    An API Request
    """
    def __init__(self, site, path, url_args, url_kwargs):
        self.site = site
        self.path = path
        self.url_args = url_args
        self.url_kwargs = url_kwargs
        #self.payload = payload
        #self.method = method
        #self.user = user
        #self.params = params
        #self.META = meta
        from hyperadmin.states import State
        self.session_state = State()
        self.endpoint_state = State()
        self.endpoint_state['resources'] = dict()
        self.endpoint_state['endpoints'] = dict()
        self.endpoint_state['link_prototypes'] = dict()
        super(APIRequest, self).__init__()
    
    @property
    def META(self):
        return self.session_state['meta']
    
    def get_response_type(self):
        """
        Returns the active response type to be used
        
        :rtype: string
        """
        val = self.META.get('HTTP_ACCEPT', '')
        media_types = self.site.media_types.keys()
        if not media_types:
            return val
        return mimeparse.best_match(media_types, val) or val
    
    def get_request_type(self):
        """
        Returns the active request type to be used
        
        :rtype: string
        """
        val = self.META.get('CONTENT_TYPE', self.META.get('HTTP_ACCEPT', ''))
        media_types = self.site.media_types.keys()
        if not media_types:
            return val
        return mimeparse.best_match(media_types, val) or val
    
    def get_request_media_type(self):
        """
        Returns the request media type to be used or raises an error
        
        :raises ValueError: when the requested content type is unrecognized
        :rtype: string
        """
        content_type = self.get_request_type()
        media_type_cls = self.site.media_types.get(content_type, None)
        if media_type_cls is None:
            raise ValueError('Unrecognized request content type "%s". Choices are: %s' % (content_type, self.site.media_types.keys()))
        return media_type_cls(self)
    
    def get_response_media_type(self):
        """
        Returns the response media type to be used or raises an error
        
        :raises ValueError: when the requested content type is unrecognized
        :rtype: string
        """
        content_type = self.get_response_type()
        media_type_cls = self.site.media_types.get(content_type, None)
        if media_type_cls is None:
            raise ValueError('Unrecognized request content type "%s". Choices are: %s' % (content_type, self.site.media_types.keys()))
        return media_type_cls(self)
    
    def get_resource(self, urlname):
        """
        Returns a bound resource matching the urlname
        
        :param urlname: The urlname to find
        :type urlname: string
        :raises KeyError: when the urlname does not match any resources
        :rtype: Resource
        """
        if urlname not in self.endpoint_state['resources']:
            resource = self.site.get_resource_from_urlname(urlname)
            if resource is None:
                raise KeyError, urlname
            bound_resource = resource.fork(api_request=self)
        return self.endpoint_state['resources'][urlname]
    
    def record_resource(self, resource):
        """
        Record the resource in our urlname cache
        
        :param resource: Resource
        """
        assert resource.api_request == self
        urlname = resource.get_url_name()
        self.endpoint_state['resources'][urlname] = resource
        
        #useful for inline resources
        if urlname not in self.site.resources_by_urlname:
            self.site.resources_by_urlname[urlname] = resource
    
    def get_endpoint(self, urlname):
        """
        Returns a bound endpoint matching the urlname
        
        :param urlname: The urlname to find
        :type urlname: string
        :raises KeyError: when the urlname does not match any endpoints
        :rtype: Endpoint
        """
        if urlname not in self.endpoint_state['endpoints']:
            endpoint = self.site.get_endpoint_from_urlname(urlname)
            if endpoint is None:
                raise KeyError, urlname
            bound_endpoint = endpoint.fork(api_request=self)
            #fork => __init__ => post_register => record_endpoint
        return self.endpoint_state['endpoints'][urlname]
    
    def record_endpoint(self, endpoint):
        """
        Record the endpoint in our urlname cache
        
        :param resource: Endpoint
        """
        assert endpoint.api_request == self
        urlname = endpoint.get_url_name()
        self.endpoint_state['endpoints'][urlname] = endpoint
    
    def get_link_prototypes(self, endpoint):
        """
        Returns the link prototypes to be used by the endpint
        
        :param endpoint: endpoint object
        :rtype: list of link prototypes
        """
        urlname = endpoint.get_url_name()
        if urlname not in self.endpoint_state['link_prototypes']:
            link_prototypes = endpoint.create_link_prototypes()
            self.endpoint_state['link_prototypes'][urlname] = link_prototypes
        return self.endpoint_state['link_prototypes'][urlname]
    
    def get_site(self):
        """
        Returns the bound site
        
        :rtype: SiteResource
        """
        if 'site' not in self.endpoint_state:
            bound_site = self.site.fork(api_request=self)
            self.endpoint_state['site'] = bound_site
            bound_site.post_register()
        return self.endpoint_state['site']
    
    def generate_response(self, link, state):
        """
        Returns a response generated from the response media type
        
        :param link: The active link representing the endpoint's response
        :param state: The endpoint's state
        :rtype: [Http]Response
        """
        media_type = self.get_response_media_type()
        response_type = self.get_response_type()
        return state.generate_response(media_type=media_type, response_type=response_type, link=link)

class InternalAPIRequest(APIRequest):
    """
    An Internal API Request
    """
    def __init__(self, site, path='/', url_args=[], url_kwargs={}, **kwargs):
        super(InternalAPIRequest, self).__init__(site, path, url_args, url_kwargs)
        kwargs.setdefault('method', 'GET')
        kwargs.setdefault('params', {})
        kwargs.setdefault('payload', {})
        for key, val in kwargs.iteritems():
            setattr(self, key, val)
    
    def get_full_path(self):
        return self.path

class HTTPAPIRequest(APIRequest):
    """
    Represents an API Request spawned from a Django HTTP Request
    """
    
    get_to_meta_map = {
        '_HTTP_ACCEPT':'HTTP_ACCEPT',
        '_CONTENT_TYPE':'CONTENT_TYPE',
    }
    
    def __init__(self, site, request, url_args, url_kwargs):
        self.request = request
        path = request.path
        super(HTTPAPIRequest, self).__init__(site=site, path=path, url_args=url_args, url_kwargs=url_kwargs)
    
    @property
    def payload(self):
        if not hasattr(self, '_payload'):
            media_type = self.get_request_media_type()
            self._payload = media_type.deserialize(self.request)
        return self._payload
    
    @property
    def method(self):
        return self.request.method
    
    def get_full_path(self):
        return self.request.get_full_path()
    
    @property
    def user(self):
        return self.session_state['auth']
    
    @property
    def params(self):
        if not hasattr(self, '_params'):
            self._params = self.request.GET.copy()
        return self._params
    
    def populate_session_data_from_request(self, request):
        #TODO consult site object
        data = {'endpoints': {},
                'resources': {},
                'request': request,
                'meta': self.patched_meta(request),
                'extra_get_params': self.get_passthrough_params(request),}
        if hasattr(request, 'user'):
            data['auth'] = request.user
        self.session_state.update(data)
        #TODO set response type & request type
        return data
    
    def patched_meta(self, request):
        meta = dict(request.META)
        for src, dst in self.get_to_meta_map.iteritems():
            if src in request.GET:
                meta[dst] = request.GET[src]
        return meta
    
    def get_passthrough_params(self, request):
        pass_through_params = dict()
        for src, dst in self.get_to_meta_map.iteritems():
            if src in request.GET:
                pass_through_params[src] = request.GET[src]
        return pass_through_params

class NamespaceAPIRequest(InternalAPIRequest):
    def __init__(self, api_request, path='/', url_args=[], url_kwargs={}, **kwargs):
        self.original_api_request = api_request
        super(NamespaceAPIRequest, self).__init__(api_request.site, path, url_args, url_kwargs, **kwargs)
        self.session_state.update(api_request.session_state)
    
    def get_full_path(self):
        #TODO
        return self.original_api_request.get_full_path()
    
    @property
    def user(self):
        return self.original_api_request.user

class Namespace(object):
    """
    Represents alternative data associated with the current api request
    
    Namespaced data is provided by another resource through an internal api request
    """
    def __init__(self, name, endpoint, state_data={}):
        self.name = name
        self.api_request = NamespaceAPIRequest(endpoint.api_request)
        self.state_data = state_data
        self.endpoint = endpoint.fork(api_request=self.api_request)
        self.endpoint.state.update(state_data)
        #self.api_request.session_state['endpoints'][self.endpoint.get_url_name()] = self.endpoint
        self.api_request.endpoint_state['resources'][self.endpoint.get_url_name()] = self.endpoint
    
    def get_namespaces(self):
        return dict()
    
    def get_prompt(self):
        return self.endpoint.get_prompt()
    
    @property
    def link(self):
        if not hasattr(self, '_link'):
            self._link = self.endpoint.get_link()
        return self._link
    
    @property
    def state(self):
        return self.endpoint.state
