#!/usr/bin/env python

import http.server
import json
import os

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if '?' in self.path:
            path, query = self.path.split('?', maxsplit=1)
        else:
            path = self.path
            query = ''

        handlers = {
            '/uppercase': self.uppercase,
        }

        try:
            handlers[path]()
        except KeyError:
            self.send_error(code=404)

    def uppercase(self):
        if self.headers['Content-Type'] != 'application/json':
            self.send_error(code=415)
            return

        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))
        q = body['q']
        response_json = {'r': q.upper()}
        response = json.dumps(response).encode('utf-8')

        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='application/json')
        self.send_header(keyword='Content-Length', value=str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET_HEAD(self, only_head: bool):
        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='text/html')
        self.end_headers()
        self.wfile.write(b'''<!DOCTYPE html>
        <html>
        <head><title>API landing page</title></head>
        <body>This is just to confirm you've reached the server.</body>
        </html>
        ''')

    def do_GET(self):
        self.do_GET_HEAD(only_head=False)

    def do_HEAD(self):
        self.do_GET_HEAD(only_head=True)

port = int(os.environ.get('PORT', '8080'))
httpd = http.server.HTTPServer(('', port), RequestHandler)
httpd.serve_forever()
