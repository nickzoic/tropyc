import wsgiref
import wsgiref.simple_server

import webob
import webob.dec
import webob.exc
import transformer
import json
import mimetypes

class HttpServer:
    
    def __init__(self, hostname="localhost", portnum=8000):

        self.urls = {}
        self.httpd = wsgiref.simple_server.make_server(hostname, portnum, self.application)

    def url(self, urlpath):
        def wrapper(func):
            self.urls[urlpath] = func
            return func
        return wrapper
    
    def rpc(self, base="/rpc/"):
        def wrapper(func):
            def inner(request):
                # XXX review this
                
                if request.content_type == 'application/x-www-form-urlencoded':
                    params = dict(request.params)
                elif request.content_type == 'application/json':
                    params = json.load(request.body_file)
                else:
                    params = None
                    
                if type(params) is dict:
                    ret = func(**params)
                elif type(params) is list:
                    ret = func(*params)
                else:
                    ret = func(params)
                    
                return webob.Response(json.dumps(ret), content_type="application/json")
            self.urls[base + func.__name__] = inner
            return func
        return wrapper

    def addfile(self, url, filename):
        mimetype, encoding = mimetypes.guess_type(filename)
        with open(filename) as fh:
            filedata = fh.read()
        
        self.urls[url] = lambda _: webob.Response(filedata, content_type=mimetype, content_encoding=encoding)
        
    def application(self, environ, start_response):
        request = webob.Request(environ)
        if request.path not in self.urls: raise webob.exc.HTTPNotFound()
        response = self.urls[request.path](request)
        return response(environ, start_response)

    def serve(self):
        self.httpd.serve_forever()


class ScriptManager:
    
    url = None
    
    def __init__(self, http_server):
        
        # XXX how to handle multiple ScriptManagers?
        self.url = "/scripts.js"
        
        http_server.url(self.url)(self.handler)
        self.scripts = []
        
    def add(self):        
        def wrapper(func):
            self.scripts.append(transformer.transform_js(func))
            return func
        return wrapper
    
    def handler(self, request):
        assert(isinstance(request,webob.Request))
        response = webob.Response(content_type="application/javascript")
        response.body = "\n\n\n".join(self.scripts)
        return response